"""Tests for the fetcher module."""

from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd

from jpstock_watchlist.fetcher import (
    apply_market_cap_bonus,
    calculate_base_score,
    fetch_stock_data,
)
from jpstock_watchlist.models import StockData


def test_calculate_base_score_high() -> None:
    score = calculate_base_score(
        roe=26.0,
        eps_growth=120.0,
        per=7.0,
        pbr=0.6,
        dividend=5.5,
        five_year_growth=110.0,
        high_52w_drop=-15.0,
    )
    # ROE >= 20: 30
    # EPS >= 50: 25
    # PER <= 10: 20
    # PBR <= 0.8: 15
    # Dividend >= 4.5: 15
    # 5Y Growth (110%): +10 (absolute threshold >= 100%)
    # Drop 15%: 4
    # Total: 30 + 25 + 20 + 15 + 15 + 10 + 4 = 119
    assert score == 119


def test_calculate_base_score_mid() -> None:
    score = calculate_base_score(
        roe=13.0,
        eps_growth=25.0,
        per=14.0,
        pbr=1.1,
        dividend=3.2,
        five_year_growth=60.0,
        high_52w_drop=-25.0,
    )
    # ROE >= 12: 20
    # EPS >= 10: 15
    # PER <= 15: 10
    # PBR <= 1.3: 8
    # Dividend >= 2.5: 8
    # 5Y Growth (60%): +5 (absolute threshold >= 50%)
    # Drop 25%: 7
    # Total: 20 + 15 + 10 + 8 + 8 + 5 + 7 = 73
    assert score == 73


def test_calculate_base_score_with_global_exclusions() -> None:
    # High metrics but PER, EPS Growth, and 5Y Growth are globally excluded
    score = calculate_base_score(
        roe=26.0,
        eps_growth=120.0,
        per=7.0,
        pbr=0.6,
        dividend=5.5,
        five_year_growth=110.0,
        high_52w_drop=-15.0,
        exclude_per=True,
        exclude_eps=True,
        exclude_growth=True,
    )
    # ROE >= 20: 30 (Active)
    # EPS >= 50: Excluded (0)
    # PER <= 10: Excluded (0)
    # PBR <= 0.8: 15 (Active)
    # Dividend >= 4.5: 15 (Active)
    # 5Y Growth >= 100: Excluded (0)
    # Drop 15%: 4 (Active)
    # Total: 30 + 15 + 15 + 4 = 64
    assert score == 64


def test_calculate_base_score_low_with_penalties() -> None:
    score = calculate_base_score(
        roe=-5.0,
        eps_growth=-15.0,
        per=55.0,
        pbr=5.0,
        dividend=1.0,
        five_year_growth=-20.0,
        high_52w_drop=-5.0,
    )
    # ROE < 0: -10
    # EPS < 0: -10
    # PER <= 60: -15
    # PBR <= 8.0: -10
    # Dividend < 1.5: 0
    # 5Y Growth (-20%): 0 (between -50% and 50%)
    # Drop < 10: 0
    # Total: -10 - 10 - 15 - 10 + 0 + 0 + 0 = -45
    assert score == -45


def test_apply_market_cap_bonus() -> None:
    # Construct dummy data
    def make_dummy(ticker: str, market_cap: float | None) -> StockData:
        return StockData(
            ticker=ticker,
            name=ticker,
            current_price=100.0,
            change_percent="0.0%",
            roe="12.0%",
            eps_growth="10.0%",
            forward_pe=12.0,
            pbr=1.0,
            dividend_yield="2.5%",
            five_year_growth="50.0%",
            high_52w_drop="10.0%",
            market_cap=market_cap,
            score=10,
        )

    data = [
        make_dummy("A", 6_000_000_000_000),
        make_dummy("B", 2_000_000_000_000),
        make_dummy("C", 200_000_000_000),
        make_dummy("D", 1_000_000),
        make_dummy("E", None),
    ]

    updated = apply_market_cap_bonus(data)
    # Base score is 79. Relative scores sum up to 125. Combined score is 204.
    # Market cap bonuses are +10, +6, +3, 0, 0.
    # Scores: A:214, B:210, C:207, D:204, E:204.
    # The output is also sorted by score descending.

    assert len(updated) == 5
    assert updated[0].ticker == "A"
    assert updated[0].score == 214
    assert updated[1].ticker == "B"
    assert updated[1].score == 210
    assert updated[2].ticker == "C"
    assert updated[2].score == 207
    assert updated[3].score == 204
    assert updated[4].score == 204


@patch("yfinance.Ticker")
def test_fetch_stock_data_roe_forecast_and_fallback(mock_ticker_cls) -> None:
    # 1. Test case: both forwardEps and bookValue exist -> forecast ROE
    mock_ticker = MagicMock()
    info_dict: dict[str, Any] = {
        "longName": "Test Stock",
        "regularMarketPrice": 100.0,
        "regularMarketChangePercent": 1.5,
        "forwardEps": 15.0,
        "bookValue": 100.0,
        "returnOnEquity": 0.12,  # historical
        "earningsQuarterlyGrowth": 0.1,
        "forwardPE": 10.0,
        "priceToBook": 1.0,
        "dividendYield": 0.03,
    }
    mock_ticker.info = info_dict
    # Mock history and splits to avoid exceptions
    mock_ticker.history.return_value = MagicMock()
    mock_ticker.splits = MagicMock()

    mock_ticker_cls.return_value = mock_ticker

    stock_data = fetch_stock_data("7203.T")
    # roe should be 15.0 / 100.0 * 100 = 15.0%
    assert stock_data.roe == "15.0%"
    assert stock_data.forward_pe == 10.0

    # 2. Test case: forwardEps is missing, falls back to returnOnEquity
    info_dict["forwardEps"] = None
    stock_data = fetch_stock_data("7203.T")
    assert stock_data.roe == "12.0%"  # 0.12 * 100

    # 3. Test case: bookValue is invalid (<= 0), falls back to returnOnEquity
    info_dict["forwardEps"] = 15.0
    info_dict["bookValue"] = 0
    stock_data = fetch_stock_data("7203.T")
    assert stock_data.roe == "12.0%"

    # 4. Test case: both are missing/None, returnOnEquity also missing -> "-"
    info_dict["forwardEps"] = None
    info_dict["returnOnEquity"] = None
    stock_data = fetch_stock_data("7203.T")
    assert stock_data.roe == "-"

    # 5. Test case: PER fallback (forwardPE exists -> use it)
    info_dict["forwardPE"] = 12.0
    info_dict["trailingPE"] = 15.0
    stock_data = fetch_stock_data("7203.T")
    assert stock_data.forward_pe == 12.0

    # 6. Test case: PER fallback (forwardPE missing -> use trailingPE)
    info_dict["forwardPE"] = None
    stock_data = fetch_stock_data("7203.T")
    assert stock_data.forward_pe == 15.0

    # 7. Test case: PER fallback (both missing -> "-")
    info_dict["forwardPE"] = None
    info_dict["trailingPE"] = None
    stock_data = fetch_stock_data("7203.T")
    assert stock_data.forward_pe == "-"


@patch("yfinance.Ticker")
def test_fetch_stock_data_re_listing_gap(mock_ticker_cls) -> None:
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "longName": "Test Gap Stock",
        "regularMarketPrice": 100.0,
        "regularMarketChangePercent": 0.0,
        "forwardEps": 10.0,
        "bookValue": 100.0,
        "returnOnEquity": 0.1,
        "earningsQuarterlyGrowth": 0.1,
        "forwardPE": 10.0,
        "priceToBook": 1.0,
        "dividendYield": 0.03,
    }

    # Create a history with a large gap (> 90 days)
    # Day 1: 2020-01-01, Price: 50.0
    # Day 2: 2020-01-02, Price: 51.0
    # (gap of 100 days)
    # Day 3: 2020-04-12, Price: 100.0
    # Day 4: 2020-04-13, Price: 101.0
    dates = pd.to_datetime(["2020-01-01", "2020-01-02", "2020-04-12", "2020-04-13"])
    history_data = {
        "Open": [50.0, 51.0, 100.0, 101.0],
        "High": [52.0, 53.0, 102.0, 103.0],
        "Low": [48.0, 49.0, 98.0, 99.0],
        "Close": [50.0, 51.0, 100.0, 101.0],
        "Volume": [1000, 1000, 1000, 1000],
    }
    history_df = pd.DataFrame(history_data, index=dates)
    mock_ticker.history.return_value = history_df
    mock_ticker.splits = pd.Series(dtype=float)

    mock_ticker_cls.return_value = mock_ticker

    stock_data = fetch_stock_data("8303.T")

    # Since there is a 100-day gap between 2020-01-02 and 2020-04-12,
    # the history should be sliced to start from 2020-04-12.
    # Therefore, the start price for 5-year growth should be 100.0, and the end price is 101.0.
    # Expected growth: (101.0 / 100.0 - 1) * 100 = 1.0%
    assert stock_data.five_year_growth == "1.0%"
    assert stock_data.is_short_history is True  # history length is 2 (< 500)
