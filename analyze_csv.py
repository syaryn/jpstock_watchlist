"""CSV stock analysis batch application entry point."""

# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=15.0.0",
#     "tabulate>=0.10.0",
# ]
# ///

import argparse
from datetime import UTC, datetime
from pathlib import Path

from jpstock_watchlist.csv_analyzer import load_and_analyze_csv
from jpstock_watchlist.csv_models import CSVStockData
from jpstock_watchlist.formatter import format_market_cap


def parse_args() -> str:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze brokerage stock list CSV and calculate investment scores."
    )
    parser.add_argument(
        "--input",
        type=str,
        help=(
            "Path to the input CSV file. If omitted, the latest file from "
            "input/ directory will be used."
        ),
    )
    args = parser.parse_args()

    if args.input:
        return args.input

    # Auto-selection logic: Find latest csv in input/
    input_dir = Path("input")
    if not input_dir.exists() or not input_dir.is_dir():
        from rich.console import Console

        err_console = Console(stderr=True)
        err_console.print("[bold red]Error:[/] 'input/' directory does not exist.")
        raise SystemExit(1)

    csv_files = sorted(input_dir.glob("*.csv"), key=lambda p: p.name, reverse=True)
    if not csv_files:
        from rich.console import Console

        err_console = Console(stderr=True)
        err_console.print(
            "[bold red]Error:[/] No CSV files found in 'input/' directory."
        )
        raise SystemExit(1)

    selected_file = csv_files[0]
    return str(selected_file)


def format_cell(val: object, style_type: str) -> str:
    """Format metric value for consistent display."""
    if val == "-" or val is None:
        return "-"
    try:
        if isinstance(val, (int, float, str)):
            f_val = float(val)
            if style_type == "percent":
                return f"{f_val:.2f}%"
            elif style_type == "percent_1d":
                return f"{f_val:.1f}%"
            elif style_type == "percent_signed":
                return f"{f_val:+.1f}%"
            elif style_type == "sigma":
                return f"{f_val:+.2f}σ"  # noqa: RUF001
            elif style_type == "times":
                return f"{f_val:.2f}"
    except ValueError, TypeError:
        pass
    return str(val)


def save_csv_report_to_markdown(
    data: list[CSVStockData],
    output_dir: Path = Path("output"),
) -> Path:
    """Save stock analysis results to a markdown table."""
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(UTC).strftime("%Y%m%d")
    output_file = output_dir / f"csv_{today}.md"

    # Assemble markdown table rows manually
    # to match headers and handle cumulative JPY line
    headers = [
        "コード",
        "会社名",
        "市場",
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

    markdown_rows = []
    markdown_rows.append("| " + " | ".join(headers) + " |")
    markdown_rows.append("| " + " | ".join(aligns) + " |")

    cumulative_total = 0.0
    boundary_inserted = False

    for s in data:
        price_val = 0.0
        if isinstance(s.current_price, (int, float)):
            price_val = float(s.current_price)

        stock_cost = price_val * 100

        # Boundary logic
        if not boundary_inserted and (cumulative_total + stock_cost) > 2_400_000:
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
            ]
            markdown_rows.append("| " + " | ".join(boundary_row) + " |")
            boundary_inserted = True

        cumulative_total += stock_cost

        row_cells = [
            s.ticker,
            s.name,
            s.market,
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

    # Add header
    header_text = (
        f"# CSV Stock Analysis Watchlist - {datetime.now(UTC).strftime('%Y-%m-%d')}\n\n"
    )
    full_content = header_text + "\n".join(markdown_rows) + "\n"

    output_file.write_text(full_content, encoding="utf-8")
    return output_file


def main() -> None:
    """Execute CSV analysis batch."""
    input_file = parse_args()

    try:
        analyzed_data = load_and_analyze_csv(input_file)
    except Exception as e:
        from rich.console import Console

        err_console = Console(stderr=True)
        err_console.print(f"[bold red]Error parsing CSV file:[/] {e}")
        raise SystemExit(1) from e

    from rich import box
    from rich.console import Console
    from rich.table import Table

    console = Console()
    console.print(f"[bold]Selected Input File:[/] [cyan]{input_file}[/]")
    console.print(f"[green]Successfully analyzed[/] {len(analyzed_data)} stocks")

    # Construct stdout terminal Table
    table = Table(title="CSV Stock Watchlist (330 pts Max)", box=box.SIMPLE_HEAVY)
    table.add_column("コード", style="bold")
    table.add_column("会社名")
    table.add_column("市場")
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

    for s in analyzed_data:
        price_val = 0.0
        if isinstance(s.current_price, (int, float)):
            price_val = float(s.current_price)

        stock_cost = price_val * 100

        # Boundary limit line in Rich
        if not boundary_inserted and (cumulative_total + stock_cost) > 2_400_000:
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
            )
            boundary_inserted = True

        cumulative_total += stock_cost

        table.add_row(
            s.ticker,
            s.name,
            s.market,
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

    console.print(table)

    # Save output to Markdown file
    output_file = save_csv_report_to_markdown(analyzed_data)
    console.print(f"[blue]Saved CSV report to:[/] {output_file}")


if __name__ == "__main__":
    main()
