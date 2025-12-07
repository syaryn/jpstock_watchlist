"""Stock data fetcher using yfinance API."""

import yfinance as yf

from jpstock_watchlist.models import StockData


def calculate_score(
    roe: float,
    eps_growth: float,
    per: float | str,
    pbr: float | str,
    dividend: float,
) -> int:
    """Calculate investment score based on financial metrics.

    Args:
        roe: Return on Equity percentage
        eps_growth: EPS quarterly growth percentage
        per: Forward P/E ratio or '-' if unavailable
        pbr: Price to Book ratio or '-' if unavailable
        dividend: Dividend yield percentage

    Returns:
        Investment score (0-155, max across all metrics)
    """
    score = 0

    # ROE scoring (max 50 points)
    if roe >= 25:
        score += 50
    elif roe >= 20:
        score += 45
    elif roe >= 18:
        score += 42
    elif roe >= 15:
        score += 38
    elif roe >= 12:
        score += 32
    elif roe >= 10:
        score += 25
    elif roe >= 8:
        score += 18
    elif roe >= 5:
        score += 10
    elif roe > 0:
        score += 5

    # EPS growth scoring (max 35 points)
    if eps_growth >= 100:
        score += 35
    elif eps_growth >= 70:
        score += 30
    elif eps_growth >= 50:
        score += 27
    elif eps_growth >= 30:
        score += 22
    elif eps_growth >= 10:
        score += 15
    elif eps_growth >= 0:
        score += 8
    elif eps_growth >= -20:
        score += 3
    # else: score += 0 (below -20%)

    # P/E ratio scoring (max 30 points)
    if isinstance(per, (int, float)):
        if per <= 8:
            score += 30
        elif per <= 10:
            score += 27
        elif per <= 12:
            score += 23
        elif per <= 15:
            score += 18
        elif per <= 18:
            score += 12
        elif per <= 20:
            score += 8
        elif per <= 25:
            score += 3
        # else: score += 0 (>25 or unavailable)

    # PBR scoring (max 25 points)
    if isinstance(pbr, (int, float)):
        if pbr <= 0.7:
            score += 25
        elif pbr <= 0.9:
            score += 22
        elif pbr <= 1.1:
            score += 18
        elif pbr <= 1.3:
            score += 14
        elif pbr <= 1.6:
            score += 10
        elif pbr <= 2.0:
            score += 5
        # else: score += 0 (>2.0 or unavailable)

    # Dividend yield scoring (max 15 points)
    if dividend >= 5:
        score += 15
    elif dividend >= 4.5:
        score += 13
    elif dividend >= 4:
        score += 11
    elif dividend >= 3.5:
        score += 9
    elif dividend >= 3:
        score += 7
    elif dividend >= 2.5:
        score += 5
    elif dividend >= 2:
        score += 3
    # else: score += 0 (<2%)

    return score


def fetch_stock_data(ticker: str) -> StockData:
    """Fetch stock data from yfinance and calculate metrics.

    Args:
        ticker: Stock ticker symbol (e.g., '7203.T')

    Returns:
        StockData model with all financial metrics and score
    """
    stock = yf.Ticker(ticker)
    info = stock.info

    # Extract metrics
    roe_raw = info.get("returnOnEquity", 0)
    roe = (roe_raw * 100) if roe_raw else 0

    eps_growth_raw = info.get("earningsQuarterlyGrowth", 0)
    eps_growth = (eps_growth_raw * 100) if eps_growth_raw else 0

    per = info.get("forwardPE", "-")
    pbr = info.get("priceToBook", "-")

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

    # Calculate score
    score = calculate_score(roe, eps_growth, per, pbr, dividend)

    # Build StockData model
    return StockData(
        ticker=ticker,
        name=info.get("longName", ticker),
        current_price=info.get("regularMarketPrice", "-"),
        change_percent=f"{info.get('regularMarketChangePercent', 0):.2f}%",
        roe=f"{roe:.1f}%",
        eps_growth=f"{eps_growth:.1f}%",
        forward_pe=per,
        pbr=pbr,
        dividend_yield=f"{dividend:.2f}%",
        score=score,
    )


def fetch_watchlist(tickers: list[str]) -> list[StockData]:
    """Fetch stock data for multiple tickers.

    Args:
        tickers: List of stock ticker symbols

    Returns:
        List of StockData models sorted by score (descending)
    """
    data = [fetch_stock_data(ticker) for ticker in tickers]
    return sorted(data, key=lambda x: x.score, reverse=True)
