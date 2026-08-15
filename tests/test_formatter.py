"""Tests for the formatter module."""

from pathlib import Path

from jpstock_watchlist.formatter import (
    create_rich_table,
    format_cell,
    format_markdown_table,
    format_market_cap,
    save_csv_report_to_markdown,
)
from jpstock_watchlist.models import CSVStockData


def test_format_market_cap() -> None:
    assert format_market_cap(None) == "-"
    assert format_market_cap("invalid") == "invalid"
    assert format_market_cap(1_500_000_000_000) == "1.50兆円"
    assert format_market_cap(200_000_000) == "2.00億円"
    assert format_market_cap(50_000_000) == "50,000,000円"
    assert format_market_cap(1_000_000_000_000) == "1.00兆円"
    assert format_market_cap(100_000_000) == "1.00億円"


def test_format_cell() -> None:
    assert format_cell(None, "percent") == "-"
    assert format_cell(None, "times") == "-"
    assert format_cell(12.3456, "percent") == "12.35%"
    assert format_cell(12.3456, "percent_1d") == "12.3%"
    assert format_cell(5.6, "percent_signed") == "+5.6%"
    assert format_cell(-5.6, "percent_signed") == "-5.6%"
    assert format_cell(1.23, "sigma") == "+1.23σ"  # noqa: RUF001
    assert format_cell(15.4, "times") == "15.40"
    assert format_cell(0.0, "times") == "0.00"


def make_dummy_stock(
    ticker: str, price: float, score: int, is_jpx400: bool = False
) -> CSVStockData:
    return CSVStockData(
        ticker=ticker,
        name=f"Stock {ticker}",
        market="プライム",
        sector="情報・通信業",
        current_price=price,
        market_cap=1_000_000_000_000,
        roe=15.0,
        roic=12.0,
        dividend_yield=3.5,
        peg_ratio=1.0,
        div_growth_3y=20.0,
        predicted_per=14.0,
        pbr=1.2,
        relative_52w=40.0,
        payout_ratio_total=50.0,
        payout_ratio=35.0,
        score=score,
        is_jpx400=is_jpx400,
    )


def test_format_markdown_table_with_boundary() -> None:
    # Stock 1: 15,000 JPY * 100 = 1,500,000 JPY (Total: 1.5M <= 2.4M)
    # Stock 2: 10,000 JPY * 100 = 1,000,000 JPY (Total: 2.5M > 2.4M -> triggers boundary!)
    # Stock 3: 5,000 JPY * 100 = 500,000 JPY
    data = [
        make_dummy_stock("7203.T", 15000.0, 300, is_jpx400=True),
        make_dummy_stock("6861.T", 10000.0, 280),
        make_dummy_stock("8035.T", 5000.0, 260),
    ]

    table_md = format_markdown_table(data)
    assert "7203.T" in table_md
    assert "6861.T" in table_md
    assert "8035.T" in table_md
    assert "〇" in table_md  # noqa: RUF001
    assert "累計240万円ライン" in table_md
    assert "ここまでの累計: 1,500,000円" in table_md


def test_format_markdown_table_missing_price_no_boundary() -> None:
    # Stock 1 has no price (None), so cumulative calculation is unknown and boundary should NOT be emitted
    data = [
        make_dummy_stock("7203.T", 15000.0, 300),
        CSVStockData(
            ticker="9999.T",
            name="No Price Stock",
            market="プライム",
            sector="サービス",
            current_price=None,
            market_cap=None,
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
            score=280,
        ),
        make_dummy_stock("8035.T", 10000.0, 260),
    ]

    table_md = format_markdown_table(data)
    assert "7203.T" in table_md
    assert "9999.T" in table_md
    assert "8035.T" in table_md
    assert "累計240万円ライン" not in table_md


def test_save_csv_report_to_markdown(tmp_path: Path) -> None:
    data = [
        make_dummy_stock("7203.T", 2000.0, 300),
    ]
    output_file = save_csv_report_to_markdown(data, output_dir=tmp_path)
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "# CSV Stock Analysis Watchlist" in content
    assert "7203.T" in content


def test_create_rich_table() -> None:
    data = [
        make_dummy_stock("7203.T", 20000.0, 300, is_jpx400=True),
        make_dummy_stock("6861.T", 10000.0, 280),
    ]
    table = create_rich_table(data)
    assert table.title == "CSV Stock Watchlist (350 pts Max)"
    assert len(table.rows) == 3  # Stock 1, Boundary line, Stock 2
