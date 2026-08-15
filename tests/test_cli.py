"""Tests for CLI module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from jpstock_watchlist.cli import main, parse_args


def test_parse_args_explicit() -> None:
    with patch("sys.argv", ["jpstock", "--input", "custom_path.csv"]):
        input_file = parse_args()
        assert input_file == "custom_path.csv"


def test_parse_args_auto(tmp_path: Path) -> None:
    # Create test CSV files
    csv1 = tmp_path / "screening_20260101.csv"
    csv2 = tmp_path / "screening_20260102.csv"
    csv1.write_text("コード,会社名\n", encoding="utf-8")
    csv2.write_text("コード,会社名\n", encoding="utf-8")

    with (
        patch("sys.argv", ["jpstock"]),
        patch("jpstock_watchlist.cli.settings.input_dir", tmp_path),
    ):
        input_file = parse_args()
        assert input_file == str(csv2)


def test_parse_args_missing_dir(tmp_path: Path) -> None:
    with (
        patch("sys.argv", ["jpstock"]),
        patch("jpstock_watchlist.cli.settings.input_dir", tmp_path / "nonexistent"),
        pytest.raises(SystemExit),
    ):
        parse_args()


def test_parse_args_no_csv(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with (
        patch("sys.argv", ["jpstock"]),
        patch("jpstock_watchlist.cli.settings.input_dir", empty_dir),
        pytest.raises(SystemExit),
    ):
        parse_args()


def test_main_execution(tmp_path: Path) -> None:
    # Create test CSV
    csv_file = tmp_path / "test_screening.csv"
    csv_file.write_text(
        "コード,会社名,市場,業種,[基本項目]直近終値,[基礎条件]時価総額\n"
        "7203,トヨタ自動車,東プ,輸送用機器,2500,400000\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "output"

    with (
        patch("sys.argv", ["jpstock", "--input", str(csv_file)]),
        patch("jpstock_watchlist.cli.settings.output_dir", output_dir),
        patch("rich.console.Console.print") as mock_print,
    ):
        main()
        assert mock_print.called
        assert output_dir.exists()
        assert any(output_dir.glob("csv_*.md"))


def test_main_error_handling() -> None:
    with (
        patch("sys.argv", ["jpstock", "--input", "nonexistent.csv"]),
        pytest.raises(SystemExit),
    ):
        main()
