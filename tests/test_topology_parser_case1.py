"""
Tests for Eurostag topology parsing using the case1 fixtures.
"""
from deeac.enums import BusType, GeneratorType


def test_case1_topology_counts(case1_topology):
    """
    Validate that case1 topology produces the expected core counts.
    """
    assert case1_topology.base_power == 100
    assert len(case1_topology.buses) == 11
    assert len(case1_topology.generators) == 4
    assert len(case1_topology.loads) == 6
    assert len(case1_topology.branches) == 13


def test_case1_topology_slack_bus(case1_topology):
    """
    Ensure the slack bus is detected and typed correctly.
    """
    slack_buses = [bus for bus in case1_topology.buses if bus.type == BusType.SLACK]
    assert len(slack_buses) == 1
    assert slack_buses[0].name == "NHVCEQ"


def test_case1_topology_generator_type(case1_topology):
    """
    Ensure a known generator is parsed with the expected type.
    """
    gen = next(generator for generator in case1_topology.generators if generator.name == "GENA1")
    assert gen.tpe == GeneratorType.PV
