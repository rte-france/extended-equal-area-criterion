"""Tests for Dynawo node-breaker terminal resolution."""

import sys
from types import ModuleType

if "pypowsybl" not in sys.modules:
    sys.modules["pypowsybl"] = ModuleType("pypowsybl")
else:
    pass

from deeac.IO.dynawo.dynawo_parser import resolve_dynawo_terminal_bus_id

if "pypowsybl" in sys.modules:
    del sys.modules["pypowsybl"]
else:
    pass


def test_node_breaker_terminal_uses_busbar_section() -> None:
    """Prefer the IIDM busbar section for a node-breaker terminal.

    :return: Return value.
    """
    row: dict[str, object] = dict(
        voltage_level1_id="VL_1",
        node1=7,
        bus1_id="SOLVED_BUS_0",
    )
    node_bus_ids: dict[tuple[str, str], str] = dict()
    node_bus_ids[("VL_1", "7")] = "BBS_7"

    resolved_bus_id: str = resolve_dynawo_terminal_bus_id(row, 1, node_bus_ids)

    assert resolved_bus_id == "BBS_7"


def test_bus_breaker_terminal_keeps_solved_bus() -> None:
    """Keep the solved bus when no node-breaker mapping exists.

    :return: Return value.
    """
    row: dict[str, object] = dict(
        voltage_level_id="VL_1",
        node=None,
        bus_id="BUS_1",
    )

    resolved_bus_id: str = resolve_dynawo_terminal_bus_id(row, None, dict())

    assert resolved_bus_id == "BUS_1"
