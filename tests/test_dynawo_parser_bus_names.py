"""Tests for stable IEEE14 bus names in the public Dynawo parser path."""

from pathlib import Path

from deeac.IO.dynawo.dynawo_parser import IidmParser


def test_ieee14_deeac_bus_names_remain_stable() -> None:
    """Verify the parsed IEEE14 network keeps the established DEEAC names."""
    iidm_path: Path = (
        Path(__file__).parent
        / "data"
        / "dynawo_success_case"
        / "inputs"
        / "IEEE14.iidm"
    )
    network = IidmParser(str(iidm_path)).parse()
    bus_names: set[str] = {bus.name for bus in network.buses}
    expected_bus_names: set[str] = {
        "BUS    1",
        "BUS    2",
        "BUS    3",
        "BUS    4",
        "BUS    5",
        "BUS    6",
        "BUS    7",
        "BUS    8",
        "BUS    9",
        "BUS   10",
        "BUS   11",
        "BUS   12",
        "BUS   13",
        "BUS   14",
    }

    assert bus_names == expected_bus_names
