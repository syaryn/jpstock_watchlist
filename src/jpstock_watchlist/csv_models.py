"""Stock watchlist data models for CSV based batch."""

from dataclasses import dataclass


@dataclass(slots=True)
class CSVStockData:
    """Stock watchlist data model from CSV metrics with scoring."""

    ticker: str
    name: str
    market: str
    sector: str
    current_price: float | str
    market_cap: float | None

    # Financial indicators
    roe: float | str
    roic: float | str
    dividend_yield: float | str
    peg_ratio: float | str
    div_growth_3y: float | str
    predicted_per: float | str
    pbr: float | str
    relative_52w: float | str
    payout_ratio_total: float | str
    payout_ratio: float | str

    score: int
