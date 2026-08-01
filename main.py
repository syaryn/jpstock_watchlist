"""jpstock-watchlist main application entry point."""

# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pandas>=3.0.2",
#     "pydantic>=2.13.3",
#     "pydantic-settings>=2.14.0",
#     "rich>=15.0.0",
#     "tabulate>=0.10.0",
#     "yfinance>=1.3.0",
# ]
# ///

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich import box
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from jpstock_watchlist.config import settings
from jpstock_watchlist.fetcher import apply_market_cap_bonus, fetch_stock_data
from jpstock_watchlist.formatter import format_market_cap, save_to_markdown


def parse_args() -> list[str]:
    parser = argparse.ArgumentParser(
        description="Fetch and display JP stock watchlist."
    )
    parser.add_argument(
        "--tickers",
        type=str,
        help=(
            "Comma-separated list of stock tickers (e.g. 7203.T,6861.T). "
            "Falls back to TICKERS env var if not set."
        ),
    )
    args = parser.parse_args()

    tickers_str = args.tickers or settings.tickers
    if not tickers_str or not tickers_str.strip():
        err_console = Console(stderr=True)
        err_console.print("[bold red]Error:[/] No tickers provided.")
        err_console.print(
            "Provide tickers via --tickers argument or TICKERS environment variable.\n"
            "e.g., uv run python main.py --tickers 7203.T,6861.T"
        )
        raise SystemExit(1)

    return [ticker.strip() for ticker in tickers_str.split(",") if ticker.strip()]


def main() -> None:
    """Execute the main application logic."""
    console = Console()
    tickers = parse_args()

    console.print(f"[bold]Fetching[/] {len(tickers)} stocks: {', '.join(tickers)}")

    # Fetch stock data
    watchlist_data = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching data", total=len(tickers))

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {
                executor.submit(fetch_stock_data, ticker): ticker for ticker in tickers
            }

            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                progress.update(task, description=f"Fetched {ticker}")
                watchlist_data.append(future.result())
                progress.advance(task)

    # Sort data after concurrent fetch so table is consistently ordered if desired,
    # but apply_market_cap_bonus already sorts by score, so we are good.
    watchlist_data = apply_market_cap_bonus(watchlist_data)

    console.print(f"[green]Done[/] fetched data for {len(watchlist_data)} stocks")

    # Display table in terminal
    table = Table(title="Stock Watchlist", box=box.SIMPLE_HEAVY)
    table.add_column("ティッカー", style="bold")
    table.add_column("銘柄")
    table.add_column("現在値", justify="right")
    table.add_column("前日比%", justify="right")
    table.add_column("ROE", justify="right")
    table.add_column("EPS成長", justify="right")
    table.add_column("予想PER", justify="right")
    table.add_column("PBR", justify="right")
    table.add_column("予想配当%", justify="right")
    table.add_column("5年騰落", justify="right")
    table.add_column("高値下落%", justify="right")
    table.add_column("時価総額", justify="right")
    table.add_column("スコア", justify="right")

    cumulative_total = 0.0
    boundary_inserted = False

    for stock in watchlist_data:
        price_val = 0.0
        if stock.current_price != "-":
            try:
                price_val = float(stock.current_price)
            except ValueError, TypeError:
                pass

        stock_cost = price_val * 100

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
            )
            boundary_inserted = True

        cumulative_total += stock_cost

        table.add_row(
            stock.ticker,
            stock.name,
            str(stock.current_price),
            str(stock.change_percent),
            str(stock.roe),
            str(stock.eps_growth),
            str(stock.forward_pe),
            str(stock.pbr),
            str(stock.dividend_yield),
            str(stock.five_year_growth),
            str(stock.high_52w_drop),
            format_market_cap(stock.market_cap),
            str(stock.score),
        )

    console.print(table)

    # Save to markdown file
    output_file = save_to_markdown(watchlist_data)
    console.print(f"[blue]Saved[/] watchlist to: {output_file}")


if __name__ == "__main__":
    main()
