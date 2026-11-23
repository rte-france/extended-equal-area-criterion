"""Regressions for several equipment trips belonging to one Dynawo fault."""

from pathlib import Path

import pytest

from deeac.IO.dynawo.dynawo_parser import (
    DynawoBlackBoxModel,
    DynawoConnect,
    DynawoParametersParser,
    build_dynawo_fault_events,
    parse_dyd_connects,
    parse_dyd_models,
    is_event_connected_to_fault,
)
from deeac.IO.dynawo.parse_dynawo import parse_dynawo
from deeac.Models.events.branch_event import BranchEvent
from deeac.Models.events.fault_events import FaultEvents
from deeac.Models.network import Network


@pytest.mark.parametrize("line_fault", (False, True))
@pytest.mark.parametrize("switch_off", (False, True))
def test_multiple_disconnections(tmp_path: Path, line_fault: bool, switch_off: bool) -> None:
    """
    Read all simultaneous branch trips and apply them to the network.

    :param tmp_path: Temporary directory for the scenario XML.
    :param line_fault: Whether to use a line fault instead of a bus fault.
    :param switch_off: Whether a signal also disconnects the faulted line.
    :return: None.
    """
    # Use public IIDM equipment so the test exercises static-id resolution too.
    case_dir: Path = Path(__file__).parent / "data" / "IEEE14" / "Dynawo"
    dyd_file: Path = tmp_path / "events.dyd"
    par_file: Path = tmp_path / "events.par"
    fault_model: str
    fault_connection: str
    switch_connection: str
    if line_fault:
        fault_model = '<blackBoxModel id="Fault" lib="LineFault" parId="Fault" staticId="_BUS____1-BUS____2-1_AC"/>'
        fault_connection = ""
        switch_connection = '<connect id1="Trip" var1="event_state1_value" id2="Fault" var2="line_switchOffSignal1_value"/>'
    else:
        fault_model = '<blackBoxModel id="Fault" lib="NodeFault" parId="Fault"/>'
        fault_connection = '<connect id1="Fault" var1="fault_terminal" id2="NETWORK" var2="_BUS____1_TN_ACPIN"/>'
        switch_connection = '<connect id1="Trip" var1="event_state1_value" id2="Fault" var2="fault_switchOffSignal_value"/>'
    if switch_off:
        pass
    else:
        switch_connection = ""
    dyd_file.write_text(
        f'''<dynamicModelsArchitecture>
        {fault_model}
        {fault_connection}
        {switch_connection}
        <blackBoxModel id="Trip" lib="EventQuadripoleDisconnection" parId="Trip"/>
        <blackBoxModel id="TransformerTrip" lib="EventQuadripoleDisconnection" parId="Trip"/>
        <blackBoxModel id="LaterTrip" lib="EventQuadripoleDisconnection" parId="LaterTrip"/>
        <connect id1="Trip" var1="event_state1_value" id2="NETWORK" var2="_BUS____1-BUS____2-1_AC_state_value"/>
        <connect id1="Trip" var1="event_state1_value" id2="NETWORK" var2="_BUS____1-BUS____5-1_AC_state_value"/>
        <connect id1="TransformerTrip" var1="event_state1_value" id2="NETWORK" var2="_BUS____4-BUS____9-1_PT_state_value"/>
        <connect id1="TransformerTrip" var1="event_state1_value" id2="NETWORK" var2="_BUS____4-BUS____9-1_PT_state_value"/>
        <connect id1="LaterTrip" var1="event_state1_value" id2="NETWORK" var2="_BUS____2-BUS____3-1_AC_state_value"/>
        </dynamicModelsArchitecture>''',
        encoding="utf-8",
    )
    par_file.write_text(
        '''<parametersSet>
        <set id="Fault">
          <par type="DOUBLE" name="fault_tBegin" value="1"/>
          <par type="DOUBLE" name="fault_tEnd" value="1.1"/>
          <par type="DOUBLE" name="line_tBegin" value="1"/>
          <par type="DOUBLE" name="line_tEnd" value="1.1"/>
        </set>
        <set id="Trip"><par type="DOUBLE" name="event_tEvent" value="1.1"/></set>
        <set id="LaterTrip"><par type="DOUBLE" name="event_tEvent" value="2"/></set>
        </parametersSet>''',
        encoding="utf-8",
    )
    models: dict[str, DynawoBlackBoxModel] = parse_dyd_models(str(dyd_file))
    connects: list[DynawoConnect] = parse_dyd_connects(str(dyd_file))
    parameters: dict[str, dict[str, object]] = DynawoParametersParser(
        str(dyd_file), str(par_file)
    ).parse_par(str(par_file))
    faults: list[FaultEvents] = build_dynawo_fault_events(
        str(case_dir / "IEEE14.iidm"), models, connects, parameters
    )
    assert len(faults) == 1
    fault: FaultEvents = faults[0]
    openings: list[BranchEvent] = [event for event in fault.mitigation_events if isinstance(event, BranchEvent)]
    # Duplicate wiring must not duplicate openings; the later trip is unrelated.
    assert len(openings) == 6
    assert all(event.time == 1.1 and not event.breaker_closed for event in openings)

    network: Network = parse_dynawo(
        jobs_file=None,
        iidm_file=str(case_dir / "IEEE14.iidm"),
        dyd_file=str(case_dir / "IEEE14.dyd"),
        par_file=str(case_dir / "IEEE14.par"),
    )
    for failure in fault.failure_events:
        failure.apply_to_network(network)
    for mitigation in fault.mitigation_events:
        mitigation.apply_to_network(network)
    assert not network.get_branch("BUS    1", "BUS    2")["1"].closed_at_first_bus
    assert not network.get_branch("BUS    1", "BUS    2")["1"].closed_at_second_bus
    assert not network.get_branch("BUS    4", "BUS    9")["1"].closed_at_first_bus
    assert not network.get_branch("BUS    4", "BUS    9")["1"].closed_at_second_bus
    assert not network.get_branch("BUS    1", "BUS    5")["1"].closed_at_first_bus
    assert not network.get_branch("BUS    1", "BUS    5")["1"].closed_at_second_bus
    assert network.get_branch("BUS    2", "BUS    3")["1"].closed_at_first_bus
    assert network.get_branch("BUS    2", "BUS    3")["1"].closed_at_second_bus


def test_explicit_fault_connection_overrides_matching_time() -> None:
    """
    Keep a trip assigned to its explicitly connected fault.

    :return: None.
    """
    models: dict[str, DynawoBlackBoxModel] = dict()
    models["FirstFault"] = DynawoBlackBoxModel("FirstFault", "NodeFault", "Fault", None)
    models["SecondFault"] = DynawoBlackBoxModel("SecondFault", "LineFault", "Fault", None)
    models["Trip"] = DynawoBlackBoxModel("Trip", "EventQuadripoleDisconnection", "Trip", None)
    connects: list[DynawoConnect] = list()
    connects.append(DynawoConnect("Trip", "event_state1_value", "SecondFault", "line_switchOffSignal1_value"))
    parameters: dict[str, dict[str, object]] = dict()
    parameters["Trip"] = dict(event_tEvent=1.1)

    # Both faults clear at 1.1 s, but only the second receives this trip signal.
    assert not is_event_connected_to_fault("Trip", "FirstFault", models, connects, parameters, 1.1)
    assert is_event_connected_to_fault("Trip", "SecondFault", models, connects, parameters, 1.1)
