"""Stock data models with Pydantic validation."""

from pydantic import BaseModel, Field


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
    score: int = Field(..., ge=0, le=155, description="Investment score (0-155)")

    class Config:
        """Pydantic model configuration."""

        frozen = True
