"""jpstock-watchlist main application entry point."""

import os
import sys

from jpstock_watchlist.fetcher import fetch_watchlist
from jpstock_watchlist.formatter import save_to_markdown


def main() -> None:
    """Execute the main application logic."""
    # Get tickers from environment variable
    tickers_env = os.getenv("TICKERS")
    if not tickers_env:
        print("Error: TICKERS environment variable not set", file=sys.stderr)
        print(
            "Set TICKERS via environment (mise loads .env) "
            "e.g., TICKERS=7203.T,6861.T,8035.T",
            file=sys.stderr,
        )
        sys.exit(1)

    # Parse tickers from comma-separated string
    tickers = [ticker.strip() for ticker in tickers_env.split(",")]
    print(f"Fetching data for {len(tickers)} stocks: {', '.join(tickers)}")

    # Fetch stock data
    watchlist_data = fetch_watchlist(tickers)
    print(f"Successfully fetched data for {len(watchlist_data)} stocks")

    # Save to markdown file
    output_file = save_to_markdown(watchlist_data)
    print(f"Watchlist saved to: {output_file}")


if __name__ == "__main__":
    main()
