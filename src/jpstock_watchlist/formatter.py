"""Markdown formatter for stock watchlist data."""

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jpstock_watchlist.models import StockData


def format_market_cap(value: float | str | None) -> str:
    """Format market capitalization with Japanese units."""
    if value is None:
        return "-"
    if isinstance(value, str):
        raw_value = value
        try:
            value = float(value)
        except ValueError:
            return raw_value

    if value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}兆円"
    if value >= 100_000_000:
        return f"{value / 100_000_000:.2f}億円"
    return f"{value:,.0f}円"


def format_markdown_table(data: list[StockData]) -> str:
    """Format stock data as markdown table with a 2.4 million JPY boundary."""
    processed_rows = []
    cumulative_total = 0.0
    boundary_inserted = False

    for stock in data:
        price_val = 0.0
        if stock.current_price != "-":
            try:
                price_val = float(stock.current_price)
            except ValueError, TypeError:
                pass

        stock_cost = price_val * 100

        # Boundary row when total > 2.4M JPY
        if not boundary_inserted and (cumulative_total + stock_cost) > 2_400_000:
            cum_text = (
                f"**↑ 累計240万円ライン (ここまでの累計: {int(cumulative_total):,}円)**"
            )
            processed_rows.append(
                {
                    "ticker": "---",
                    "name": cum_text,
                    "current_price": "---",
                    "change_percent": "---",
                    "roe": "---",
                    "eps_growth": "---",
                    "forward_pe": "---",
                    "pbr": "---",
                    "dividend_yield": "---",
                    "five_year_growth": "---",
                    "high_52w_drop": "---",
                    "market_cap": None,
                    "score": "---",
                    "is_per_missing": False,
                    "is_eps_missing": False,
                    "is_short_history": False,
                }
            )
            boundary_inserted = True

        cumulative_total += stock_cost
        processed_rows.append(stock.model_dump())

    # Convert to DataFrame for easy table generation
    import pandas as pd

    df = pd.DataFrame(processed_rows)

    # Drop internal metadata columns if they exist
    for col in ["is_per_missing", "is_eps_missing", "is_short_history"]:
        if col in df.columns:
            df = df.drop(columns=[col])

    # Rename columns to Japanese
    df = df.rename(
        columns={
            "ticker": "ティッカー",
            "name": "銘柄",
            "current_price": "現在値",
            "change_percent": "前日比%",
            "roe": "ROE",
            "eps_growth": "EPS成長",
            "forward_pe": "予想PER",
            "pbr": "PBR",
            "dividend_yield": "予想配当%",
            "five_year_growth": "5年騰落",
            "high_52w_drop": "高値下落%",
            "market_cap": "時価総額",
            "score": "スコア",
        }
    )

    if "時価総額" in df.columns:
        df["時価総額"] = df["時価総額"].apply(format_market_cap)

    # Generate markdown table
    return df.to_markdown(index=False)  # type: ignore[return-value]


def save_to_markdown(
    data: list[StockData],
    output_dir: Path = Path("output"),
) -> Path:
    """Save stock watchlist data to markdown file.

    Args:
        data: List of StockData models (should be sorted by score)
        output_dir: Directory to save the markdown file

    Returns:
        Path to the created markdown file
    """
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with current date (yyyymmdd.md)
    today = datetime.now(UTC).strftime("%Y%m%d")
    output_file = output_dir / f"{today}.md"

    # Format data as markdown table
    markdown_content = format_markdown_table(data)

    # Add header
    header = f"# Stock Watchlist - {datetime.now(UTC).strftime('%Y-%m-%d')}\n\n"
    full_content = header + markdown_content + "\n"

    # Write to file
    output_file.write_text(full_content, encoding="utf-8")

    return output_file
