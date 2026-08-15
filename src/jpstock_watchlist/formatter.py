"""Markdown and Rich table formatter for stock watchlist data."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from rich import box
from rich.table import Table

from jpstock_watchlist.models import CSVStockData

JST = ZoneInfo("Asia/Tokyo")
NISA_GROWTH_LIMIT_JPY = 2_400_000


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


def format_cell(val: float | None, style_type: str) -> str:
    """Format metric value for consistent display."""
    if val is None:
        return "-"

    if style_type == "percent":
        return f"{val:.2f}%"
    elif style_type == "percent_1d":
        return f"{val:.1f}%"
    elif style_type == "percent_signed":
        return f"{val:+.1f}%"
    elif style_type == "sigma":
        return f"{val:+.2f}σ"  # noqa: RUF001
    elif style_type == "times":
        return f"{val:.2f}"

    return str(val)


def format_markdown_table(data: list[CSVStockData]) -> str:
    """Format CSV stock data as markdown table with a 2.4 million JPY boundary."""
    headers = [
        "コード",
        "会社名",
        "市場",
        "JPX400",
        "業種",
        "直近終値",
        "時価総額",
        "実績ROE",
        "ROIC",
        "予想配当利回り",
        "予想PEGレシオ",
        "3年配当成長率",
        "予想PER",
        "PBR",
        "52週株価相対水準",
        "配当性向",
        "総還元性向",
        "スコア",
    ]

    aligns = [
        ":---",
        ":---",
        ":---",
        ":---",
        ":---",
        "---:",
        "---:",
        "---:",
        "---:",
        "---:",
        "---:",
        "---:",
        "---:",
        "---:",
        "---:",
        "---:",
        "---:",
        "---:",
    ]

    markdown_rows = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(aligns) + " |",
    ]

    cumulative_total = 0.0
    boundary_inserted = False

    for s in data:
        price_val = s.current_price if s.current_price is not None else 0.0
        stock_cost = price_val * 100

        # Boundary logic
        if (
            not boundary_inserted
            and (cumulative_total + stock_cost) > NISA_GROWTH_LIMIT_JPY
        ):
            cum_text = (
                f"**↑ 累計240万円ライン (ここまでの累計: {int(cumulative_total):,}円)**"
            )
            boundary_row = [
                "---",
                cum_text,
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
            ]
            markdown_rows.append("| " + " | ".join(boundary_row) + " |")
            boundary_inserted = True

        cumulative_total += stock_cost

        row_cells = [
            s.ticker,
            s.name,
            s.market,
            "〇" if s.is_jpx400 else "-",  # noqa: RUF001
            s.sector,
            format_cell(s.current_price, "times"),
            format_market_cap(s.market_cap),
            format_cell(s.roe, "percent"),
            format_cell(s.roic, "percent"),
            format_cell(s.dividend_yield, "percent"),
            format_cell(s.peg_ratio, "times"),
            format_cell(s.div_growth_3y, "percent"),
            format_cell(s.predicted_per, "times"),
            format_cell(s.pbr, "times"),
            format_cell(s.relative_52w, "percent_1d"),
            format_cell(s.payout_ratio, "percent_1d"),
            format_cell(s.payout_ratio_total, "percent_1d"),
            str(s.score),
        ]
        markdown_rows.append("| " + " | ".join(row_cells) + " |")

    return "\n".join(markdown_rows)


def save_csv_report_to_markdown(
    data: list[CSVStockData],
    output_dir: Path = Path("output"),
) -> Path:
    """Save stock analysis results to a markdown table file with JST timestamp.

    Args:
        data: List of CSVStockData models (sorted by score)
        output_dir: Output directory path

    Returns:
        Path to the saved markdown file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(JST).strftime("%Y%m%d")
    output_file = output_dir / f"csv_{today}.md"

    table_content = format_markdown_table(data)
    header_text = (
        f"# CSV Stock Analysis Watchlist - {datetime.now(JST).strftime('%Y-%m-%d')}\n\n"
    )
    full_content = header_text + table_content + "\n"

    output_file.write_text(full_content, encoding="utf-8")
    return output_file


def create_rich_table(
    data: list[CSVStockData],
    title: str = "CSV Stock Watchlist (350 pts Max)",
) -> Table:
    """Create a Rich Table for terminal display with 2.4M JPY line."""
    table = Table(title=title, box=box.SIMPLE_HEAVY)
    table.add_column("コード", style="bold")
    table.add_column("会社名")
    table.add_column("市場")
    table.add_column("JPX400", justify="center")
    table.add_column("業種")
    table.add_column("直近終値", justify="right")
    table.add_column("時価総額", justify="right")
    table.add_column("実績ROE", justify="right")
    table.add_column("ROIC", justify="right")
    table.add_column("予想配当%", justify="right")
    table.add_column("予想PEG", justify="right")
    table.add_column("3年配当成長", justify="right")
    table.add_column("予想PER", justify="right")
    table.add_column("PBR", justify="right")
    table.add_column("52週水準", justify="right")
    table.add_column("配当性向", justify="right")
    table.add_column("総還元性向", justify="right")
    table.add_column("スコア", justify="right")

    cumulative_total = 0.0
    boundary_inserted = False

    for s in data:
        price_val = s.current_price if s.current_price is not None else 0.0
        stock_cost = price_val * 100

        # Boundary limit line in Rich
        if (
            not boundary_inserted
            and (cumulative_total + stock_cost) > NISA_GROWTH_LIMIT_JPY
        ):
            rich_cum_text = f"[bold yellow]↑ 累計240万円ライン (ここまでの累計: {int(cumulative_total):,}円)[/]"
            table.add_row(
                "---",
                rich_cum_text,
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
                "---",
            )
            boundary_inserted = True

        cumulative_total += stock_cost

        table.add_row(
            s.ticker,
            s.name,
            s.market,
            "[bold green]〇[/]" if s.is_jpx400 else "-",  # noqa: RUF001
            s.sector,
            format_cell(s.current_price, "times"),
            format_market_cap(s.market_cap),
            format_cell(s.roe, "percent"),
            format_cell(s.roic, "percent"),
            format_cell(s.dividend_yield, "percent"),
            format_cell(s.peg_ratio, "times"),
            format_cell(s.div_growth_3y, "percent"),
            format_cell(s.predicted_per, "times"),
            format_cell(s.pbr, "times"),
            format_cell(s.relative_52w, "percent_1d"),
            format_cell(s.payout_ratio, "percent_1d"),
            format_cell(s.payout_ratio_total, "percent_1d"),
            str(s.score),
        )

    return table


# Backwards compatibility aliases
save_to_markdown = save_csv_report_to_markdown
