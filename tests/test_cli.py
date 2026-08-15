"""Tests for CLI module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from jpstock_watchlist.cli import main, parse_args


def test_parse_args_explicit() -> None:
    with patch("sys.argv", ["jpstock", "--input", "input/screening_20260620.csv"]):
        input_file = parse_args()
        assert input_file == "input/screening_20260620.csv"


def test_parse_args_auto() -> None:
    with patch("sys.argv", ["jpstock"]):
        input_file = parse_args()
        assert input_file.endswith(".csv")


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


def test_main_execution() -> None:
    with (
        patch("sys.argv", ["jpstock", "--input", "input/screening_20260620.csv"]),
        patch("rich.console.Console.print") as mock_print,
    ):
        main()
        assert mock_print.called


def test_main_error_handling() -> None:
    with (
        patch("sys.argv", ["jpstock", "--input", "nonexistent.csv"]),
        pytest.raises(SystemExit),
    ):
        main()
