"""Stock data fetcher using yfinance API."""

import math

import pandas as pd
import yfinance as yf

from jpstock_watchlist.models import StockData

ROE_THRESHOLDS = [
    (25, 50),
    (20, 45),
    (18, 42),
    (15, 38),
    (12, 32),
    (10, 25),
    (8, 18),
    (5, 10),
    (0.001, 5),  # > 0
]

EPS_GROWTH_THRESHOLDS = [
    (100, 35),
    (70, 30),
    (50, 27),
    (30, 22),
    (10, 15),
    (0, 8),
    (-20, 3),
]

PER_THRESHOLDS = [
    (8, 30),
    (10, 27),
    (12, 23),
    (15, 18),
    (18, 12),
    (20, 8),
    (25, 3),
]

PBR_THRESHOLDS = [
    (0.7, 25),
    (0.9, 22),
    (1.1, 18),
    (1.3, 14),
    (1.6, 10),
    (2.0, 5),
]

DIVIDEND_THRESHOLDS = [
    (5, 15),
    (4.5, 13),
    (4, 11),
    (3.5, 9),
    (3, 7),
    (2.5, 5),
    (2, 3),
]

FIVE_YEAR_GROWTH_THRESHOLDS = [
    (100, 10),
    (50, 5),
]

HIGH_52W_DROP_THRESHOLDS = [
    (50, 15),
    (40, 12),
    (30, 9),
    (20, 6),
    (10, 3),
]


def _adjust_prices_for_splits(
    hist: pd.DataFrame, splits: pd.Series
) -> tuple[pd.DataFrame, float]:
    """
    Adjust prices backward using stock splits and return the adjusted history and total unadjusted ratio.
    Yahoo Finance sometimes leaves recent splits unadjusted in historical data.
    """
    if splits is None or splits.empty:
        return hist, 1.0

    hist_adjusted = hist.copy()
    total_unadjusted_split_ratio = 1.0

    for split_date, ratio in splits.items():
        if ratio <= 0:
            continue

        # Find the max price in the 5 days before the split date and the price just after
        before_split = hist_adjusted[hist_adjusted.index < split_date].tail(5)
        after_split = hist_adjusted[hist_adjusted.index >= split_date]

        if not before_split.empty and not after_split.empty:
            price_before_max = float(before_split["Close"].max())
            price_after = float(after_split["Close"].iloc[0])

            # If the price dropped by roughly the split ratio, it hasn't been adjusted by Yahoo
            implied_ratio = price_before_max / price_after

            if implied_ratio > ratio * 0.7:
                # Needs adjustment: all dates strictly before the ex-date should be adjusted.
                # However, since the drop could have happened 1-2 days before the split_date,
                # we adjust all dates where the price was still high.
                # A simpler approach is to adjust everything before `after_split.index[0]`.
                # Wait, what if the ex-date was 1 day before split_date, then the price on ex-date is already low!
                # We should adjust everything before the date where the price dropped.
                # To find the exact drop date, we find the first day in `before_split` where the price is < price_before_max * 0.7.
                # Or just adjust everything before `split_date`, but wait! If the ex-date is before `split_date`,
                # the price on the ex-date in `hist_adjusted` will be divided by ratio again! That's wrong!

                # Let's find the exact date the drop happened within `before_split` or `after_split`
                # Combine the 5 days before and 1 day after
                window = pd.concat([before_split, after_split.head(1)])
                # Find the first day where the price is less than price_before_max / (ratio * 0.7)
                drop_threshold = price_before_max / (ratio * 0.7)
                drop_dates = window[window["Close"] < drop_threshold].index
                if len(drop_dates) > 0:
                    actual_drop_date = drop_dates[0]
                    mask = hist_adjusted.index < actual_drop_date
                    for col in ["Open", "High", "Low", "Close"]:
                        if col in hist_adjusted.columns:
                            hist_adjusted.loc[mask, col] = (
                                hist_adjusted.loc[mask, col] / ratio
                            )

                    total_unadjusted_split_ratio *= ratio

    return hist_adjusted, total_unadjusted_split_ratio


def _score_from_thresholds(
    value: float, thresholds: list[tuple[float, int]], reverse: bool = False
) -> int:
    for threshold, score in thresholds:
        if reverse:
            if value <= threshold:
                return score
        else:
            if value >= threshold:
                return score
    return 0


def calculate_base_score(
    roe: float,
    eps_growth: float,
    per: float | str,
    pbr: float | str,
    dividend: float,
    five_year_growth: float,
    high_52w_drop: float,
    is_short_history: bool = False,
    exclude_roe: bool = False,
    exclude_eps: bool = False,
    exclude_per: bool = False,
    exclude_pbr: bool = False,
    exclude_dividend: bool = False,
    exclude_growth: bool = False,
    exclude_drop: bool = False,
) -> int:
    """Calculate investment score based on a balanced, risk-adjusted scorecard with global exclusion support.

    Args:
        roe: Return on Equity percentage
        eps_growth: EPS quarterly growth percentage
        per: Forward P/E ratio or '-' if unavailable
        pbr: Price to Book ratio or '-' if unavailable
        dividend: Dividend yield percentage
        five_year_growth: Five-year stock price growth percentage
        high_52w_drop: High drop percentage from 52-week high
        is_short_history: Flag indicating if the stock has short-term listing history
        exclude_roe: Flag to exclude ROE from scoring
        exclude_eps: Flag to exclude EPS growth from scoring
        exclude_per: Flag to exclude PER from scoring
        exclude_pbr: Flag to exclude PBR from scoring
        exclude_dividend: Flag to exclude Dividend from scoring
        exclude_growth: Flag to exclude 5-year growth from scoring
        exclude_drop: Flag to exclude 52-week high drop from scoring

    Returns:
        Investment score under the new risk-adjusted rules
    """
    score = 0

    # 1. ROE (Max +30, penalty down to -20)
    if not exclude_roe:
        if roe <= -10:
            score += -20
        elif roe < 0:
            score += -10
        elif roe >= 20:
            score += 30
        elif roe >= 15:
            score += 25
        elif roe >= 12:
            score += 20
        elif roe >= 10:
            score += 15
        elif roe >= 5:
            score += 10

    # 2. EPS Growth (Max +25, penalty down to -20)
    if not exclude_eps:
        if eps_growth <= -30:
            score += -20
        elif eps_growth < 0:
            score += -10
        elif eps_growth >= 50:
            score += 25
        elif eps_growth >= 30:
            score += 20
        elif eps_growth >= 10:
            score += 15
        elif eps_growth >= 0:
            score += 5

    # 3. PER (Max +20, penalty down to -25, or -15 if missing/negative)
    if not exclude_per:
        if per == "-" or per is None or (isinstance(per, (int, float)) and per <= 0):
            # Rule A Exemption: If profitable (ROE > 0), do not apply the -15 penalty (neutral 0 points)
            if roe > 0:
                score += 0
            else:
                score += -15
        elif isinstance(per, (int, float)):
            if per <= 10:
                score += 20
            elif per <= 12:
                score += 15
            elif per <= 15:
                score += 10
            elif per <= 20:
                score += 5
            elif per <= 25:
                score += 0
            elif per <= 40:
                score += -5
            elif per <= 60:
                score += -15
            else:
                score += -25

    # 4. PBR (Max +15, penalty down to -20, or -10 if missing/negative)
    if not exclude_pbr:
        if pbr == "-" or pbr is None or (isinstance(pbr, (int, float)) and pbr <= 0):
            score += -10
        elif isinstance(pbr, (int, float)):
            if pbr <= 0.8:
                score += 15
            elif pbr <= 1.0:
                score += 12
            elif pbr <= 1.3:
                score += 8
            elif pbr <= 1.6:
                score += 4
            elif pbr <= 2.0:
                score += 0
            elif pbr <= 4.0:
                score += -5
            elif pbr <= 8.0:
                score += -10
            else:
                score += -20

    # 5. Dividend Yield (Max +15)
    if not exclude_dividend:
        if dividend >= 4.5:
            score += 15
        elif dividend >= 3.5:
            score += 12
        elif dividend >= 2.5:
            score += 8
        elif dividend >= 1.5:
            score += 4

    # 6. 5-Year Price Growth (Absolute threshold-based score)
    if not exclude_growth:
        if five_year_growth >= 100.0:
            score += 10
        elif five_year_growth >= 50.0:
            score += 5
        elif five_year_growth <= -100.0:
            score += 0 if is_short_history else -10
        elif five_year_growth <= -50.0:
            score += 0 if is_short_history else -5

    # 7. 52-Week High Drop (Max +10, penalty of -30 if collapse)
    if not exclude_drop:
        drop_pct = abs(high_52w_drop)
        if drop_pct >= 80:
            score += -30
        elif drop_pct >= 50:
            score += -15
        elif drop_pct >= 30:
            score += 10
        elif drop_pct >= 20:
            score += 7
        elif drop_pct >= 10:
            score += 4

    return score


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    index = (len(sorted_values) - 1) * p
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return sorted_values[int(index)]
    fraction = index - lower
    return (
        sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction
    )


def _derive_market_cap_thresholds(
    market_caps: list[float],
) -> tuple[float, float, float]:
    """Return fixed market cap thresholds for large-cap bonus."""
    if not market_caps:
        return (math.inf, math.inf, math.inf)
    return (5_000_000_000_000, 1_000_000_000_000, 100_000_000_000)


def _market_cap_bonus(
    market_cap: float | None, thresholds: tuple[float, float, float]
) -> int:
    if market_cap is None:
        return 0
    high, mid, low = thresholds
    if market_cap >= high:
        return 10
    if market_cap >= mid:
        return 6
    if market_cap >= low:
        return 3
    return 0


def apply_market_cap_bonus(data: list[StockData]) -> list[StockData]:
    """Apply market cap bonus and dynamic global exclusions based on the current distribution."""
    # 1. Evaluate list for global exclusions
    exclude_per = any(s.is_per_missing for s in data if s.current_price != "-")
    exclude_eps = any(s.is_eps_missing for s in data if s.current_price != "-")
    exclude_growth = any(
        s.five_year_growth == "-" or s.five_year_growth is None
        for s in data
        if s.current_price != "-"
    )

    exclusions = []
    if exclude_per:
        exclusions.append("予想PER (PER)")
    if exclude_eps:
        exclusions.append("EPS成長 (EPS Growth)")
    if exclude_growth:
        exclusions.append("5年騰落 (5-Year Growth)")

    if exclusions:
        print(
            f"\n[Watchlist] データ異常/欠損検知により、以下項目を全銘柄のスコア算出から『グローバル除外』します: {', '.join(exclusions)}\n"
        )

    market_caps = [
        cap for cap in (stock.market_cap for stock in data) if isinstance(cap, float)
    ]
    thresholds = _derive_market_cap_thresholds(market_caps)

    # 2. Parse metrics to find best values for relative scoring
    valid_stocks = [s for s in data if s.current_price != "-"]

    def parse_pct(val: str | None) -> float:
        if not val or val == "-":
            return 0.0
        return float(val.replace("%", ""))

    def parse_val(val: object) -> float | str:
        if not val or val == "-":
            return "-"
        return float(str(val))

    roes = []
    eps_growths = []
    pers = []
    pbrs = []
    dividends = []
    growths = []
    drops = []

    for s in valid_stocks:
        roes.append(parse_pct(s.roe))
        eps_growths.append(parse_pct(s.eps_growth))
        per_val = parse_val(s.forward_pe)
        if isinstance(per_val, (int, float)) and per_val > 0:
            pers.append(per_val)
        pbr_val = parse_val(s.pbr)
        if isinstance(pbr_val, (int, float)) and pbr_val > 0:
            pbrs.append(pbr_val)
        dividends.append(parse_pct(s.dividend_yield))
        growths.append(parse_pct(s.five_year_growth))
        drops.append(abs(parse_pct(s.high_52w_drop)))

    max_roe = max(roes) if roes else 0.0
    max_eps = max(eps_growths) if eps_growths else 0.0
    min_per = min(pers) if pers else 0.0
    min_pbr = min(pbrs) if pbrs else 0.0
    max_div = max(dividends) if dividends else 0.0
    max_growth = max(growths) if growths else 0.0
    min_drop = min(drops) if drops else 0.0

    updated = []
    for s in data:
        if s.current_price == "-":
            # Error stock
            updated.append(s)
            continue

        roe = parse_pct(s.roe)
        eps = parse_pct(s.eps_growth)
        per = parse_val(s.forward_pe)
        pbr = parse_val(s.pbr)
        div = parse_pct(s.dividend_yield)
        growth = parse_pct(s.five_year_growth)
        drop = parse_pct(s.high_52w_drop)

        # Calculate base score with dynamic exclusions
        base_score = calculate_base_score(
            roe=roe,
            eps_growth=eps,
            per=per,
            pbr=pbr,
            dividend=div,
            five_year_growth=growth,
            high_52w_drop=drop,
            is_short_history=s.is_short_history,
            exclude_per=exclude_per,
            exclude_eps=exclude_eps,
            exclude_growth=exclude_growth,
        )

        # Calculate relative scores and sum them up
        rel_score = 0

        # ROE (Max 30)
        if max_roe > 0:
            rel_score += round((roe / max_roe) * 30.0)

        # EPS Growth (Max 25)
        if not exclude_eps and max_eps > 0:
            rel_score += round((eps / max_eps) * 25.0)

        # PER (Max 20)
        if not exclude_per:
            if isinstance(per, (int, float)) and per > 0 and min_per > 0:
                rel_score += round((min_per / per) * 20.0)

        # PBR (Max 15)
        if isinstance(pbr, (int, float)) and pbr > 0 and min_pbr > 0:
            rel_score += round((min_pbr / pbr) * 15.0)

        # Dividend Yield (Max 15)
        if max_div > 0:
            rel_score += round((div / max_div) * 15.0)

        # 5-Year Growth (Max 10)
        if not exclude_growth and max_growth > 0:
            if s.is_short_history and growth < 0:
                pass
            else:
                rel_score += round((growth / max_growth) * 10.0)

        # 52-Week High Drop (Max 10)
        # Smaller drop is better
        rel_score += round(max(0.0, (100.0 - abs(drop)) / (100.0 - min_drop) * 10.0))

        # Re-apply market cap bonus on top of recalculated score
        final_score = (
            base_score + rel_score + _market_cap_bonus(s.market_cap, thresholds)
        )

        # Update model score
        s_new = s.model_copy(update={"score": final_score})
        updated.append(s_new)

    return sorted(updated, key=lambda stock: stock.score, reverse=True)


def fetch_stock_data(ticker: str) -> StockData:
    """Fetch stock data from yfinance and calculate metrics.

    Args:
        ticker: Stock ticker symbol (e.g., '7203.T')

    Returns:
        StockData model with all financial metrics and score
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Extract metrics
        # Estimate forecast ROE: forwardEps / bookValue
        forward_eps = info.get("forwardEps")
        book_value = info.get("bookValue")

        roe_val = None
        if forward_eps is not None and book_value and book_value > 0:
            roe_val = (forward_eps / book_value) * 100
        else:
            # Fall back to historical/actual ROE
            roe_raw = info.get("returnOnEquity")
            if roe_raw is not None:
                roe_val = roe_raw * 100

        # For score calculation, if ROE is missing, we use 0.0
        roe_for_score = roe_val if roe_val is not None else 0.0

        eps_growth_raw = info.get("earningsQuarterlyGrowth")
        is_eps_missing = eps_growth_raw is None
        eps_growth = (eps_growth_raw * 100) if eps_growth_raw is not None else 0

        history_raw = stock.history(period="5y")

        # 1. Clean data: remove rows where Volume is 0 or Close is NaN (exchange placeholder or glitch days)
        history_clean = (
            history_raw[history_raw["Volume"] > 0]
            if not history_raw.empty
            else history_raw
        )
        if not history_clean.empty:
            history_clean = history_clean.dropna(subset=["Close"])
            # Detect re-listing / long trading suspensions (gap > 90 days)
            # and slice to keep only the data after the most recent gap.
            if len(history_clean) >= 2:
                dates = history_clean.index
                last_gap_idx = None
                for i in range(1, len(dates)):
                    if (dates[i] - dates[i - 1]).days > 90:
                        last_gap_idx = i
                if last_gap_idx is not None:
                    history_clean = history_clean.iloc[last_gap_idx:]
        if history_clean.empty:
            history_clean = history_raw

        history_adj, unadjusted_ratio = _adjust_prices_for_splits(
            history_clean, stock.splits
        )

        # 2. Short history detection (<500 trading days/approx 2 years) to protect new listings
        history_len = len(history_clean) if not history_clean.empty else 0
        is_short_history = history_len < 500

        five_year_growth = 0.0
        five_year_growth_label = "-"
        if not history_adj.empty and "Close" in history_adj.columns:
            closes = history_adj["Close"].dropna()
            if len(closes) >= 2:
                start = float(closes.iloc[0])
                end = float(closes.iloc[-1])
                if start > 0:
                    five_year_growth = (end / start - 1) * 100
                    five_year_growth_label = f"{five_year_growth:.1f}%"

        # 3. PER Fallback: Use trailingPE if forwardPE is missing or None
        per_raw = info.get("forwardPE")
        if per_raw is None or per_raw == "-":
            per_raw = info.get("trailingPE")

        is_per_missing = per_raw is None
        per = per_raw if per_raw is not None else "-"

        if isinstance(per, (int, float)) and unadjusted_ratio > 1.0:
            # Adjust PE by multiplying with the ratio (since true EPS is lower)
            per = per * unadjusted_ratio

        pbr = info.get("priceToBook", "-")
        market_cap_raw = info.get("marketCap")
        market_cap = (
            float(market_cap_raw) if isinstance(market_cap_raw, (int, float)) else None
        )

        dividend_raw = info.get("dividendYield")
        dividend = 0.0
        if isinstance(dividend_raw, (int, float)):
            # Normalize to percentage
            if dividend_raw >= 0.1:
                # Values like 0.91, 0.96 are already percentages
                dividend = dividend_raw
            else:
                # Values like 0.0313, 0.0359 need * 100
                dividend = dividend_raw * 100

        # Handle 52-week high drop using adjusted history
        high_drop_pct = 0.0
        high_drop_label = "-"
        if not history_adj.empty and "Close" in history_adj.columns:
            # Last 252 trading days (~1 year)
            last_year_history = history_adj.tail(252)
            if not last_year_history.empty:
                high_52w = float(last_year_history["High"].max())
                current_close = float(last_year_history["Close"].iloc[-1])
                if high_52w > 0 and current_close < high_52w:
                    high_drop_pct = ((high_52w - current_close) / high_52w) * 100
                    high_drop_label = f"{-high_drop_pct:.1f}%"
                elif high_52w > 0:
                    high_drop_label = "0.0%"

        # Calculate preliminary score
        score = calculate_base_score(
            roe_for_score,
            eps_growth,
            per,
            pbr,
            dividend,
            five_year_growth,
            high_drop_pct,
            is_short_history=is_short_history,
        )

        # Build StockData model
        return StockData(
            ticker=ticker,
            name=info.get("longName", ticker),
            current_price=info.get("regularMarketPrice", "-"),
            change_percent=f"{info.get('regularMarketChangePercent', 0):.2f}%",
            roe=f"{roe_val:.1f}%" if roe_val is not None else "-",
            eps_growth=f"{eps_growth:.1f}%" if not is_eps_missing else "-",
            forward_pe=per,
            pbr=pbr,
            dividend_yield=f"{dividend:.2f}%",
            five_year_growth=five_year_growth_label,
            high_52w_drop=high_drop_label,
            market_cap=market_cap,
            score=score,
            is_per_missing=is_per_missing,
            is_eps_missing=is_eps_missing,
            is_short_history=is_short_history,
        )
    except Exception as e:
        return StockData(
            ticker=ticker,
            name=f"Error: {e!s}",
            current_price="-",
            change_percent="-",
            roe="-",
            eps_growth="-",
            forward_pe="-",
            pbr="-",
            dividend_yield="-",
            five_year_growth="-",
            high_52w_drop="-",
            market_cap=None,
            score=0,
            is_per_missing=True,
            is_eps_missing=True,
            is_short_history=True,
        )


def fetch_watchlist(tickers: list[str]) -> list[StockData]:
    """Fetch stock data for multiple tickers with dynamic global exclusion.

    Args:
        tickers: List of stock ticker symbols

    Returns:
        List of StockData models sorted by score (descending)
    """
    data = [fetch_stock_data(ticker) for ticker in tickers]
    return apply_market_cap_bonus(data)
