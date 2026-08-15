"""Stock watchlist data models for CSV screening analysis."""

from dataclasses import dataclass


@dataclass(slots=True)
class CSVStockData:
    """Stock watchlist data model from CSV metrics with scoring."""

    ticker: str
    name: str
    market: str
    sector: str
    current_price: float | None
    market_cap: float | None

    # Financial indicators
    roe: float | None
    roic: float | None
    dividend_yield: float | None
    peg_ratio: float | None
    div_growth_3y: float | None
    predicted_per: float | None
    pbr: float | None
    relative_52w: float | None
    payout_ratio_total: float | None
    payout_ratio: float | None

    score: int
    is_jpx400: bool = False


# Alias for unified naming
StockData = CSVStockData
