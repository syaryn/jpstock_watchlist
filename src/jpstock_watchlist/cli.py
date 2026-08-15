"""CLI entry point for Japanese stock screening analysis."""

import argparse

from rich.console import Console

from jpstock_watchlist.config import settings
from jpstock_watchlist.csv_analyzer import load_and_analyze_csv
from jpstock_watchlist.formatter import create_rich_table, save_csv_report_to_markdown


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
    input_dir = settings.input_dir
    if not input_dir.exists() or not input_dir.is_dir():
        err_console = Console(stderr=True)
        err_console.print(
            f"[bold red]Error:[/] '{input_dir}' directory does not exist."
        )
        raise SystemExit(1)

    csv_files = sorted(
        [p for p in input_dir.glob("*.csv") if p.name != "screener_result.csv"],
        key=lambda p: p.name,
        reverse=True,
    )
    if not csv_files:
        err_console = Console(stderr=True)
        err_console.print(
            f"[bold red]Error:[/] No screening CSV files found in '{input_dir}' directory."
        )
        raise SystemExit(1)

    selected_file = csv_files[0]
    return str(selected_file)


def main() -> None:
    """Execute CSV analysis batch and output results."""
    input_file = parse_args()
    console = Console()

    try:
        analyzed_data = load_and_analyze_csv(input_file)
    except Exception as e:
        err_console = Console(stderr=True)
        err_console.print(f"[bold red]Error parsing CSV file:[/] {e}")
        raise SystemExit(1) from e

    console.print(f"[bold]Selected Input File:[/] [cyan]{input_file}[/]")
    console.print(f"[green]Successfully analyzed[/] {len(analyzed_data)} stocks")

    # Display Rich table in terminal
    table = create_rich_table(analyzed_data)
    console.print(table)

    # Save output to Markdown file
    output_file = save_csv_report_to_markdown(
        analyzed_data, output_dir=settings.output_dir
    )
    console.print(f"[blue]Saved CSV report to:[/] {output_file}")


if __name__ == "__main__":
    main()
