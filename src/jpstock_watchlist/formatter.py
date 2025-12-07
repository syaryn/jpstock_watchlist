"""Markdown formatter for stock watchlist data."""

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from jpstock_watchlist.models import StockData


def format_markdown_table(data: list[StockData]) -> str:
    """Format stock data as markdown table.

    Args:
        data: List of StockData models

    Returns:
        Markdown-formatted table string
    """
    # Convert to DataFrame for easy table generation
    df = pd.DataFrame([stock.model_dump() for stock in data])

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
            "dividend_yield": "配当%",
            "score": "スコア",
        }
    )

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
