"""jpstock-watchlist main application entry point."""

import os

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

from jpstock_watchlist.fetcher import apply_market_cap_bonus, fetch_stock_data
from jpstock_watchlist.formatter import format_market_cap, save_to_markdown


def main() -> None:
    """Execute the main application logic."""
    console = Console()
    err_console = Console(stderr=True)

    # Get tickers from environment variable
    tickers_env = os.getenv("TICKERS")
    if tickers_env is None or not tickers_env.strip():
        err_console.print("[bold red]Error:[/] TICKERS environment variable not set")
        err_console.print(
            "Set TICKERS via environment (mise loads .env) "
            "e.g., TICKERS=7203.T,6861.T,8035.T"
        )
        raise SystemExit(1)

    # Parse tickers from comma-separated string
    tickers = [ticker.strip() for ticker in tickers_env.split(",") if ticker.strip()]
    console.print(f"[bold]Fetching[/] {len(tickers)} stocks: {', '.join(tickers)}")

    # Fetch stock data
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching data", total=len(tickers))
        watchlist_data = []
        for ticker in tickers:
            progress.update(task, description=f"Fetching {ticker}")
            watchlist_data.append(fetch_stock_data(ticker))
            progress.advance(task)

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
    table.add_column("配当%", justify="right")
    table.add_column("時価総額", justify="right")
    table.add_column("スコア", justify="right")

    for stock in watchlist_data:
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
            format_market_cap(stock.market_cap),
            str(stock.score),
        )

    console.print(table)

    # Save to markdown file
    output_file = save_to_markdown(watchlist_data)
    console.print(f"[blue]Saved[/] watchlist to: {output_file}")


if __name__ == "__main__":
    main()
