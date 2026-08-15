"""Tests for config module."""

from jpstock_watchlist.config import settings


def test_settings_defaults() -> None:
    assert settings.input_dir.name == "input"
    assert settings.output_dir.name == "output"
    assert "screener_result.csv" in str(settings.jpx400_file)
