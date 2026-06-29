"""
Tests for Eurostag event parsing using the case1 fixtures.
"""
import numpy as np

from deeac.IO.event_loader import EventLoader
from deeac.Models.events.branch_event import BranchEvent
from deeac.Models.events.line_short_circuit_event import LineShortCircuitEvent


def test_case1_event_parser_types(case1_event_parser):
    """
    Validate the parsed event types and ordering for case1.
    """
    events = case1_event_parser.parse_events()
    assert len(events) == 3
    assert isinstance(events[0], LineShortCircuitEvent)
    assert isinstance(events[1], BranchEvent)
    assert isinstance(events[2], BranchEvent)


def test_case1_event_parser_values(case1_event_parser):
    """
    Validate the parsed event payloads for the line fault case.
    """
    events = case1_event_parser.parse_events()
    fault = events[0]
    assert np.isclose(fault.time, 10.0)
    assert fault.first_bus_name == "NHVA3"
    assert fault.second_bus_name == "NHVD1"
    assert fault.parallel_id == "1"
    assert np.isclose(fault.fault_position, 0.5)


def test_case1_event_loader_split(case1_event_parser):
    """
    Ensure failure and mitigation events are separated correctly.
    """
    loader = EventLoader(case1_event_parser)
    failure_events, mitigation_events = loader.load_events()
    assert len(failure_events) == 1
    assert len(mitigation_events) == 2
