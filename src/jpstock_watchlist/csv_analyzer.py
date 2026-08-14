import csv
import math
from collections.abc import Callable
from pathlib import Path

from jpstock_watchlist.csv_models import CSVStockData


def find_col(columns: list[str], prefix: str) -> str | None:
    """Find a column name that starts with the given prefix."""
    for col in columns:
        if col.startswith(prefix):
            return col
    return None


def clean_val(val: object) -> float | str:
    """Convert value to float if valid, otherwise return '-'."""
    if val is None:
        return "-"
    try:
        if val == "" or val == "-":
            return "-"
        if isinstance(val, (int, float, str)):
            f_val = float(val)
            if math.isnan(f_val):
                return "-"
            return f_val
    except ValueError, TypeError:
        pass
    return "-"


def calculate_base_score_csv(
    roe: float | str,
    roic: float | str,
    dividend_yield: float | str,
    peg_ratio: float | str,
    div_growth_3y: float | str,
    predicted_per: float | str,
    pbr: float | str,
    relative_52w: float | str,
    payout_ratio_total: float | str,
    payout_ratio: float | str,
) -> int:
    """Calculate absolute valuation score (Max 160 points total)."""
    score = 0

    # 1. 実績ROE (Max 30 / Min -20)
    if isinstance(roe, (int, float)):
        if roe <= -10:
            score -= 20
        elif roe < 0:
            score -= 10
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

    # 2. ROIC (Max 20 / Min -15)
    if isinstance(roic, (int, float)):
        if roic <= -5:
            score -= 15
        elif roic < 0:
            score -= 10
        elif roic >= 15:
            score += 20
        elif roic >= 10:
            score += 15
        elif roic >= 7:
            score += 10
        elif roic >= 4:
            score += 5

    # 3. 予想配当利回り (Max 15 / Min 0)
    if isinstance(dividend_yield, (int, float)):
        if dividend_yield >= 4.5:
            score += 15
        elif dividend_yield >= 3.5:
            score += 12
        elif dividend_yield >= 2.5:
            score += 8
        elif dividend_yield >= 1.5:
            score += 4

    # 4. 予想PEGレシオ (Max 20 / Min -15)
    if isinstance(peg_ratio, (int, float)):
        if peg_ratio <= 0:
            score -= 15
        elif peg_ratio <= 0.5:
            score += 20
        elif peg_ratio <= 1.0:
            score += 15
        elif peg_ratio <= 1.5:
            score += 10
        elif peg_ratio <= 2.0:
            score += 5
        else:
            score -= 10

    # 5. 3年配当成長率 (Max 25 / Min -20)
    if isinstance(div_growth_3y, (int, float)):
        if div_growth_3y <= -30:
            score -= 20
        elif div_growth_3y < 0:
            score -= 10
        elif div_growth_3y >= 50:
            score += 25
        elif div_growth_3y >= 30:
            score += 20
        elif div_growth_3y >= 10:
            score += 15
        elif div_growth_3y >= 0:
            score += 5

    # 6. 予想PER (Max 10 / Min -15)
    if isinstance(predicted_per, (int, float)) and predicted_per > 0:
        if predicted_per <= 10:
            score += 10
        elif predicted_per <= 12:
            score += 8
        elif predicted_per <= 15:
            score += 6
        elif predicted_per <= 20:
            score += 4
        elif predicted_per <= 25:
            score += 0
        elif predicted_per <= 40:
            score -= 3
        elif predicted_per <= 60:
            score -= 8
        else:
            score -= 15
    else:
        # PER missing fallback: If profitable (ROE > 0) neutral, else penalty
        roe_val = roe if isinstance(roe, (int, float)) else 0.0
        if roe_val <= 0:
            score -= 8

    # 7. PBR (Max 10 / Min -15)
    if isinstance(pbr, (int, float)) and pbr > 0:
        if pbr <= 0.8:
            score += 10
        elif pbr <= 1.0:
            score += 8
        elif pbr <= 1.3:
            score += 6
        elif pbr <= 1.6:
            score += 4
        elif pbr <= 2.0:
            score += 0
        elif pbr <= 4.0:
            score -= 3
        elif pbr <= 8.0:
            score -= 8
        else:
            score -= 15
    else:
        score -= 8

    # 8. 52週株価相対水準 (Max 10 / Min -10)
    if isinstance(relative_52w, (int, float)):
        if relative_52w <= 5:
            score -= 10
        elif relative_52w >= 90:
            pass  # 高値圏の減点ペナルティを廃止 (0点)
        elif relative_52w <= 30:
            score += 10
        elif relative_52w <= 50:
            score += 5

    # 9. 総還元性向 (Max 10 / Min -5)
    if isinstance(payout_ratio_total, (int, float)):
        if payout_ratio_total < 0:
            score -= 5
        elif payout_ratio_total >= 80:
            score += 10
        elif payout_ratio_total >= 50:
            score += 8
        elif payout_ratio_total >= 30:
            score += 5
        elif payout_ratio_total >= 15:
            score += 2

    # 10. 配当性向 (Max 10 / Min -15)
    if isinstance(payout_ratio, (int, float)):
        if payout_ratio < 0:
            score -= 15
        elif payout_ratio >= 100.0:
            score -= 5
        elif payout_ratio >= 80.0:
            score += 3
        elif payout_ratio >= 60.0:
            score += 6
        elif payout_ratio >= 30.0:
            score += 10
        elif payout_ratio >= 20.0:
            score += 6
        elif payout_ratio >= 15.0:
            score += 3

    return score


def get_market_cap_bonus(market_cap: float | None) -> int:
    """Calculate Market Cap Bonus (Max 30 points)."""
    if market_cap is None:
        return 0
    if market_cap >= 1_000_000_000_000:  # 1 trillion JPY
        return 30
    if market_cap >= 300_000_000_000:  # 300 billion JPY
        return 20
    if market_cap >= 100_000_000_000:  # 100 billion JPY
        return 10
    return 0


def calculate_relative_scores_csv(
    data: list[dict],
) -> list[dict]:
    """Calculate relative scores based on percentile rank (Max 160 pts)."""
    for d in data:
        d["rel_score"] = 0

    metrics_config = [
        # (key, reverse [True=higher is better], max_pts, valid_fn, cap_fn)
        ("roe", True, 30.0, lambda v: isinstance(v, (int, float)) and v > 0, None),
        ("roic", True, 20.0, lambda v: isinstance(v, (int, float)) and v > 0, None),
        (
            "dividend_yield",
            True,
            15.0,
            lambda v: isinstance(v, (int, float)) and v >= 0,
            None,
        ),
        (
            "peg_ratio",
            False,
            20.0,
            lambda v: isinstance(v, (int, float)) and v > 0,
            None,
        ),
        (
            "div_growth_3y",
            True,
            25.0,
            lambda v: isinstance(v, (int, float)) and v > 0,
            None,
        ),
        (
            "predicted_per",
            False,
            10.0,
            lambda v: isinstance(v, (int, float)) and v > 0,
            None,
        ),
        ("pbr", False, 10.0, lambda v: isinstance(v, (int, float)) and v > 0, None),
        (
            "relative_52w",
            False,
            10.0,
            lambda v: isinstance(v, (int, float)) and v >= 0,
            None,
        ),
        (
            "payout_ratio_total",
            True,
            10.0,
            lambda v: isinstance(v, (int, float)) and v >= 0,
            lambda v: min(100.0, float(v)),
        ),
    ]

    for key, reverse, max_pts, valid_fn, cap_fn in metrics_config:
        valid_stocks = [d for d in data if valid_fn(d[key])]
        if not valid_stocks:
            continue

        def get_val(
            d: dict,
            target_key: str = key,
            target_cap_fn: Callable[[float], float] | None = cap_fn,
        ) -> float:
            val = float(d[target_key])
            if target_cap_fn is not None:
                val = target_cap_fn(val)
            return val

        sorted_stocks = sorted(valid_stocks, key=get_val, reverse=reverse)
        n = len(sorted_stocks)
        if n == 1:
            sorted_stocks[0]["rel_score"] += round(max_pts)
            continue

        # Map tied values to average percentile rank
        val_to_pct = {}
        i = 0
        while i < n:
            j = i
            v = get_val(sorted_stocks[i])
            while j < n and get_val(sorted_stocks[j]) == v:
                j += 1
            avg_rank_idx = (i + j - 1) / 2.0
            pct = (n - 1 - avg_rank_idx) / (n - 1)
            val_to_pct[v] = pct
            i = j

        for d in valid_stocks:
            v = get_val(d)
            d["rel_score"] += round(val_to_pct[v] * max_pts)

    # 10. 配当性向 (Max 10) - 30%~60% optimal zone
    for d in data:
        if isinstance(d["payout_ratio"], (int, float)):
            p = float(d["payout_ratio"])
            if 30.0 <= p <= 60.0:
                d["rel_score"] += 10
            elif 0 < p < 30.0:
                d["rel_score"] += round((p / 30.0) * 10.0)
            elif p > 60.0:
                reduction = round(((p - 60.0) / 40.0) * 10.0)
                d["rel_score"] += max(0, 10 - reduction)

    return data


def load_jpx400_tickers(
    filepath: str | Path = Path("input/screener_result.csv"),
) -> set[str]:
    """Load JPX400 stock codes from a CSV file into a set of codes/tickers."""
    path = Path(filepath)
    if not path.exists():
        return set()

    codes = set()
    for enc in ("utf-8-sig", "cp932", "utf-8"):
        try:
            with open(path, encoding=enc) as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    continue
                code_col = find_col(list(reader.fieldnames), "コード")
                if not code_col:
                    continue
                for row in reader:
                    val = row.get(code_col)
                    if val is not None:
                        code_raw = str(val).strip()
                        if code_raw.endswith(".0"):
                            code_raw = code_raw[:-2]
                        if code_raw:
                            codes.add(code_raw)
                            codes.add(f"{code_raw}.T")
                break
        except Exception:
            continue
    return codes


def load_and_analyze_csv(
    filepath: str,
    jpx400_filepath: str | Path = Path("input/screener_result.csv"),
) -> list[CSVStockData]:
    """Parse stock analysis CSV and calculate overall scores."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    jpx400_codes = load_jpx400_tickers(jpx400_filepath)

    # Read CSV with cp932/shift_jis using standard csv module
    with open(path, encoding="cp932", errors="replace") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames) if reader.fieldnames else []

        # Map column headers dynamically
        col_mapping = {
            "code": "コード",
            "name": "会社名",
            "market": "市場",
            "sector": "業種",
            "price": find_col(fieldnames, "[基本項目]直近終値"),
            "market_cap": find_col(fieldnames, "[基礎条件]時価総額"),
            "roe": find_col(fieldnames, "[指標]実績ROE"),
            "roic": find_col(fieldnames, "[指標]ROIC"),
            "yield": find_col(fieldnames, "[指標]予想配当利回り"),
            "peg": find_col(fieldnames, "[指標]予想PEGレシオ"),
            "growth": find_col(fieldnames, "[指標]3年配当成長率"),
            "predicted_per": find_col(fieldnames, "[指標]予想PER"),
            "pbr": find_col(fieldnames, "[指標]PBR"),
            "relative_52w": find_col(fieldnames, "[株価]52週株価相対水準"),
            "payout_ratio": find_col(fieldnames, "[指標]配当性向"),
            "payout": find_col(fieldnames, "[指標]総還元性向"),
        }

        # Verify essential columns exist
        for key, col in col_mapping.items():
            if col is None and key in ["code", "name", "price"]:
                raise ValueError(
                    f"Essential column mapped to {key} was not found in CSV."
                )

        raw_stocks = []
        for row in reader:
            val = row.get(col_mapping["code"])
            if val is None or str(val).strip() == "":
                raise ValueError("Stock code is missing in row.")
            code_raw = str(val).strip()
            if code_raw.endswith(".0"):
                code_raw = code_raw[:-2]
            ticker = f"{code_raw}.T"

            # Price and market cap
            price_col = col_mapping["price"]
            price = clean_val(row.get(price_col)) if price_col else "-"

            # Convert market cap from 100M JPY (億円) to JPY
            mcap_col = col_mapping["market_cap"]
            mcap_raw = row.get(mcap_col) if mcap_col else None
            mcap_clean = clean_val(mcap_raw)
            market_cap_jpy = (
                mcap_clean * 100_000_000
                if isinstance(mcap_clean, (int, float))
                else None
            )

            # Gather indicators
            roe_col = col_mapping["roe"]
            roic_col = col_mapping["roic"]
            yield_col = col_mapping["yield"]
            peg_col = col_mapping["peg"]
            growth_col = col_mapping["growth"]
            per_col = col_mapping["predicted_per"]
            pbr_col = col_mapping["pbr"]
            rel_col = col_mapping["relative_52w"]
            payout_r_col = col_mapping["payout_ratio"]
            payout_col = col_mapping["payout"]

            roe = clean_val(row.get(roe_col)) if roe_col else "-"
            roic = clean_val(row.get(roic_col)) if roic_col else "-"
            dividend_yield = clean_val(row.get(yield_col)) if yield_col else "-"
            peg_ratio = clean_val(row.get(peg_col)) if peg_col else "-"
            div_growth_3y = clean_val(row.get(growth_col)) if growth_col else "-"
            predicted_per = clean_val(row.get(per_col)) if per_col else "-"
            pbr = clean_val(row.get(pbr_col)) if pbr_col else "-"
            relative_52w = clean_val(row.get(rel_col)) if rel_col else "-"
            payout_ratio = clean_val(row.get(payout_r_col)) if payout_r_col else "-"
            payout_ratio_total = clean_val(row.get(payout_col)) if payout_col else "-"

            # Absolute score
            base_score = calculate_base_score_csv(
                roe=roe,
                roic=roic,
                dividend_yield=dividend_yield,
                peg_ratio=peg_ratio,
                div_growth_3y=div_growth_3y,
                predicted_per=predicted_per,
                pbr=pbr,
                relative_52w=relative_52w,
                payout_ratio_total=payout_ratio_total,
                payout_ratio=payout_ratio,
            )

            raw_stocks.append(
                {
                    "ticker": ticker,
                    "name": str(row.get(col_mapping["name"], "")),
                    "market": str(row.get(col_mapping["market"], "")),
                    "sector": str(row.get(col_mapping["sector"], "")),
                    "current_price": price,
                    "market_cap": market_cap_jpy,
                    "roe": roe,
                    "roic": roic,
                    "dividend_yield": dividend_yield,
                    "peg_ratio": peg_ratio,
                    "div_growth_3y": div_growth_3y,
                    "predicted_per": predicted_per,
                    "pbr": pbr,
                    "relative_52w": relative_52w,
                    "payout_ratio": payout_ratio,
                    "payout_ratio_total": payout_ratio_total,
                    "base_score": base_score,
                    "market_cap_bonus": get_market_cap_bonus(market_cap_jpy),
                }
            )

    # Apply relative scoring
    scored_stocks = calculate_relative_scores_csv(raw_stocks)

    # Convert to CSVStockData dataclasses
    results = []
    for s in scored_stocks:
        total_score = s["base_score"] + s["rel_score"] + s["market_cap_bonus"]
        code_raw = s["ticker"].split(".")[0]
        is_jpx400 = (s["ticker"] in jpx400_codes) or (code_raw in jpx400_codes)

        # Build CSVStockData
        results.append(
            CSVStockData(
                ticker=s["ticker"],
                name=s["name"],
                market=s["market"],
                sector=s["sector"],
                current_price=s["current_price"],
                market_cap=s["market_cap"],
                roe=s["roe"],
                roic=s["roic"],
                dividend_yield=s["dividend_yield"],
                peg_ratio=s["peg_ratio"],
                div_growth_3y=s["div_growth_3y"],
                predicted_per=s["predicted_per"],
                pbr=s["pbr"],
                relative_52w=s["relative_52w"],
                payout_ratio_total=s["payout_ratio_total"],
                payout_ratio=s["payout_ratio"],
                score=total_score,
                is_jpx400=is_jpx400,
            )
        )

    # Sort descending by score
    return sorted(results, key=lambda x: x.score, reverse=True)

