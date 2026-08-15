"""Unit tests for CSV stock analyzer."""

from pathlib import Path

from jpstock_watchlist.csv_analyzer import (
    calculate_base_score_csv,
    clean_val,
    find_col,
    get_market_cap_bonus,
    load_and_analyze_csv,
    load_jpx400_tickers,
    read_csv_with_fallback,
)
from jpstock_watchlist.models import CSVStockData


def test_find_col():
    cols = ["コード", "会社名", "[基本項目]直近終値(26/06/19)(円)", "PBR"]
    assert find_col(cols, "[基本項目]直近終値") == "[基本項目]直近終値(26/06/19)(円)"
    assert find_col(cols, "コード") == "コード"
    assert find_col(cols, "PER") is None


def test_clean_val():
    import pandas as pd

    # Missing / None / NaN cases
    assert clean_val(None) is None
    assert clean_val(pd.NA) is None
    assert clean_val(float("nan")) is None
    assert clean_val("-") is None
    assert clean_val("--") is None
    assert clean_val("N/A") is None
    assert clean_val("nan") is None
    assert clean_val("null") is None
    assert clean_val("") is None

    # Normal numeric inputs
    assert clean_val("12.34") == 12.34
    assert clean_val(45) == 45.0
    assert clean_val(123.456) == 123.456

    # Formatting symbols & comma stripping
    assert clean_val("1,500") == 1500.0
    assert clean_val("1,234,567.89") == 1234567.89
    assert clean_val("5.2%") == 5.2
    assert clean_val("+3.5%") == 3.5
    assert clean_val("-12.4%") == -12.4
    assert clean_val("1500円") == 1500.0
    assert clean_val("14.5倍") == 14.5

    # Full-width characters normalization (NFKC)
    assert clean_val("１２．３４") == 12.34  # noqa: RUF001
    assert clean_val("１，５００") == 1500.0  # noqa: RUF001
    assert clean_val("５．２％") == 5.2  # noqa: RUF001

    # Non-finite inputs (Infinity)
    import math

    assert clean_val(math.inf) is None
    assert clean_val(-math.inf) is None
    assert clean_val("inf") is None
    assert clean_val("-inf") is None
    assert clean_val("+inf") is None
    assert clean_val("Infinity") is None
    assert clean_val("-Infinity") is None

    # Invalid strings
    assert clean_val("abc") is None
    assert clean_val("---") is None


def test_read_csv_with_fallback(tmp_path: Path):
    # Test UTF-8 with BOM (utf-8-sig)
    utf8_file = tmp_path / "test_utf8.csv"
    utf8_file.write_text(
        "コード,会社名,市場\n7203,トヨタ自動車,東プ\n", encoding="utf-8-sig"
    )
    fieldnames, rows = read_csv_with_fallback(utf8_file)
    assert "コード" in fieldnames
    assert len(rows) == 1
    assert rows[0]["コード"] == "7203"

    # Test Shift-JIS / CP932
    cp932_file = tmp_path / "test_cp932.csv"
    cp932_file.write_text(
        "コード,会社名,市場\n6861,キーエンス,東プ\n", encoding="cp932"
    )
    fieldnames_cp, rows_cp = read_csv_with_fallback(cp932_file)
    assert "コード" in fieldnames_cp
    assert len(rows_cp) == 1
    assert rows_cp[0]["コード"] == "6861"


def test_get_market_cap_bonus():
    # 1 trillion JPY = 1_000_000_000_000 -> 30 pts
    assert get_market_cap_bonus(1_000_000_000_000) == 30
    assert get_market_cap_bonus(5_000_000_000_000) == 30
    # 300 billion JPY = 300_000_000_000 -> 20 pts
    assert get_market_cap_bonus(300_000_000_000) == 20
    assert get_market_cap_bonus(999_999_999_999) == 20
    # 100 billion JPY = 100_000_000_000 -> 10 pts
    assert get_market_cap_bonus(100_000_000_000) == 10
    assert get_market_cap_bonus(299_999_999_999) == 10
    # Less than 100 billion JPY -> 0 pts
    assert get_market_cap_bonus(99_999_999_999) == 0
    assert get_market_cap_bonus(None) == 0


def test_calculate_base_score_csv():
    # Perfect scenario (Max 160 base score)
    score = calculate_base_score_csv(
        roe=20.0,
        roic=15.0,
        dividend_yield=4.5,
        peg_ratio=0.5,
        div_growth_3y=50.0,
        predicted_per=10.0,
        pbr=0.8,
        relative_52w=20.0,
        payout_ratio_total=80.0,
        payout_ratio=45.0,
    )
    assert score == 160

    # Bad scenario
    score_bad = calculate_base_score_csv(
        roe=-15.0,  # -20
        roic=-10.0,  # -15
        dividend_yield=0.0,  # 0
        peg_ratio=2.5,  # -10
        div_growth_3y=-35.0,  # -20
        predicted_per=65.0,  # -15
        pbr=9.0,  # -15
        relative_52w=95.0,  # 0
        payout_ratio_total=-1.0,  # -5
        payout_ratio=-5.0,  # -15
    )
    assert score_bad == -115

    # None values fallback
    score_none = calculate_base_score_csv(
        roe=None,
        roic=None,
        dividend_yield=None,
        peg_ratio=None,
        div_growth_3y=None,
        predicted_per=None,
        pbr=None,
        relative_52w=None,
        payout_ratio_total=None,
        payout_ratio=None,
    )
    # PER missing (-8) + PBR missing (-8) = -16
    assert score_none == -16


def test_load_jpx400_tickers():
    tickers = load_jpx400_tickers("input/screener_result.csv")
    assert len(tickers) > 0
    assert "7203" in tickers
    assert "7203.T" in tickers


def test_load_and_analyze_csv():
    # Test loading real screening CSV in input/
    data = load_and_analyze_csv("input/screening_20260620.csv")
    assert len(data) > 0
    assert isinstance(data[0], CSVStockData)
    assert any(s.is_jpx400 for s in data)

    # Assert sorted descending by score
    for i in range(len(data) - 1):
        assert data[i].score >= data[i + 1].score

    # Test loading screening CSV with alphanumeric stock code (e.g. 167A)
    data_new = load_and_analyze_csv("input/screening_20260712.csv")
    assert len(data_new) > 0
    assert any(item.ticker == "167A.T" for item in data_new)

    for i in range(len(data_new) - 1):
        assert data_new[i].score >= data_new[i + 1].score
