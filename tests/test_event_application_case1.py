"""
Integration test for applying events to a parsed network.
"""
from deeac.IO.event_loader import EventLoader
from deeac.enums import NetworkState
from deeac.main import apply_events_to_network
from deeac.Models.network import NetworkComputed
from deeac.Models.events.fault_events import FaultEvents


def test_case1_event_application(case1_network, case1_event_parser):
    """
    Ensure that failure and mitigation events build during/post fault states.
    """
    computed = NetworkComputed()
    case1_network.initialize_simplified_network(computed)

    loader = EventLoader(case1_event_parser)
    failure_events, mitigation_events = loader.load_events()
    fault_events = FaultEvents(
        failure_events=failure_events,
        mitigation_events=mitigation_events,
        name=case1_event_parser.name,
    )
    case1_network.add_fault_events(fault_events)
    apply_events_to_network(case1_network, computed, fault_events)

    assert case1_network.get_state(computed, NetworkState.DURING_FAULT) is not None
    assert case1_network.get_state(computed, NetworkState.POST_FAULT) is not None
