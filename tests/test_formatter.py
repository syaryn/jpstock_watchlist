"""Tests for the formatter module."""

from jpstock_watchlist.formatter import format_market_cap


def test_format_market_cap() -> None:
    assert format_market_cap(None) == "-"
    assert format_market_cap("invalid") == "invalid"
    assert format_market_cap(1_500_000_000_000) == "1.50兆円"
    assert format_market_cap(200_000_000) == "2.00億円"
    assert format_market_cap(50_000_000) == "50,000,000円"
    assert format_market_cap(1_000_000_000_000) == "1.00兆円"
    assert format_market_cap(100_000_000) == "1.00億円"
