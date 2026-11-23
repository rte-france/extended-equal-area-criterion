"""Regression checks for fault input selection and Dynawo bus names."""

from pathlib import Path

import pytest

from deeac.IO.arguments_parser import EurostagRunConfiguration
from deeac.IO.dynawo.dynawo_parser import parse_dynawo_bus_terminal_name


def test_sequence_source_priority(tmp_path: Path) -> None:
    """Select the explicit list, then the folder, then the single file."""
    folder_file: Path = tmp_path / "folder.seq"
    folder_file.touch()
    config: EurostagRunConfiguration = EurostagRunConfiguration(
        "case.ech", "case.dta", "case.lf", None, None,
        "single.seq", str(tmp_path), ["explicit.seq"], 0.0, 1, 0.0,
    )
    assert config.seq_files == ["explicit.seq"]
    config = EurostagRunConfiguration(
        "case.ech", "case.dta", "case.lf", None, None,
        "single.seq", str(tmp_path), None, 0.0, 1, 0.0,
    )
    assert config.seq_files == [str(folder_file)]
    config = EurostagRunConfiguration(
        "case.ech", "case.dta", "case.lf", None, None,
        "single.seq", None, None, 0.0, 1, 0.0,
    )
    assert config.seq_files == ["single.seq"]
    with pytest.raises(ValueError):
        EurostagRunConfiguration(
            "case.ech", "case.dta", "case.lf", None, None,
            None, None, None, 0.0, 1, 0.0,
        )


def test_dynawo_bus_terminal_names() -> None:
    """Preserve RTE names while accepting the existing IEEE convention."""
    assert parse_dynawo_bus_terminal_name("_BRAUDP71_TN_ACPIN") == "BRAUDP71"
    assert parse_dynawo_bus_terminal_name("_BUS____3_TN_ACPIN") == "BUS    3"
    assert parse_dynawo_bus_terminal_name("BRAUDP71") is None
