"""Stock data models with Pydantic validation."""

from pydantic import BaseModel, ConfigDict, Field


class StockData(BaseModel):
    """Stock watchlist data model with scoring metrics."""

    ticker: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Company name")
    current_price: float | str = Field(..., description="Current market price")
    change_percent: str = Field(
        ..., description="Price change percentage from previous day"
    )
    roe: str = Field(..., description="Return on Equity percentage")
    eps_growth: str = Field(..., description="EPS growth percentage")
    forward_pe: float | str = Field(..., description="Forward P/E ratio")
    pbr: float | str = Field(..., description="Price to Book ratio")
    dividend_yield: str = Field(..., description="Dividend yield percentage")
    five_year_growth: str = Field(..., description="Five-year price growth percentage")
    high_52w_drop: str = Field(..., description="Drop percentage from 52-week high")
    market_cap: float | None = Field(
        None, description="Market capitalization in JPY, if available"
    )
    score: int = Field(
        ..., ge=-100, le=200, description="Investment score (-100 to 200)"
    )
    is_per_missing: bool = Field(False, description="Flag indicating if PER is missing")
    is_eps_missing: bool = Field(
        False, description="Flag indicating if EPS quarterly growth is missing"
    )
    is_short_history: bool = Field(
        False, description="Flag indicating if stock has a short listing history"
    )

    model_config = ConfigDict(frozen=False)
