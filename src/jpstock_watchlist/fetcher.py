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
        Investment score (0-100)
    """
    score = 0

    # ROE scoring (max 30 points)
    if roe > 15:
        score += 30
    elif roe > 10:
        score += 20

    # EPS growth scoring (max 25 points)
    if eps_growth > 20:
        score += 25
    elif eps_growth > 0:
        score += 15

    # P/E ratio scoring (max 20 points)
    if isinstance(per, (int, float)) and per < 15:
        score += 20
    elif isinstance(per, (int, float)) and per < 20:
        score += 10

    # PBR scoring (max 15 points)
    if isinstance(pbr, (int, float)) and pbr < 1.5:
        score += 15

    # Dividend yield scoring (max 10 points)
    if dividend > 3:
        score += 10

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
        dividend = dividend_raw * 100 if dividend_raw < 1 else float(dividend_raw)

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
