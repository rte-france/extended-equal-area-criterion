# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest
from typing import List

from tests import TEST_DATA_FOLDER
from deeac.adapters.events.eurostag import EventDescription, EventType, EurostagEventParser
from deeac.adapters.events.eurostag.event_parser import EVENT_DESCRIPTION
from deeac.domain.ports.dtos.events import (
    Event, LineShortCircuitEvent, BusShortCircuitEvent, BreakerPosition, BreakerEvent, BranchEvent
)
from deeac.domain.ports.dtos import Value, Unit


@pytest.fixture
def breaker_line_event_description() -> EventDescription:
    return EVENT_DESCRIPTION[EventType.BREAKER_OPEN]


@pytest.fixture
def line_short_circuit_event_description() -> EventDescription:
    return EVENT_DESCRIPTION[EventType.LINE_FAULT]


@pytest.fixture
def bus_short_circuit_clearing_event_description() -> EventDescription:
    return EVENT_DESCRIPTION[EventType.NODE_CLEAR]


@pytest.fixture
def line_short_circuit_clearing_event_description() -> EventDescription:
    return EVENT_DESCRIPTION[EventType.LINE_CLEAR]


@pytest.fixture
def breaker_line_event_record() -> str:
    return "   10.13 BRANC OP    NODE1-NODE2   -2 S          1                           0.           F       0."


@pytest.fixture
def bus_short_circuit_clearing_event_record() -> str:
    return "  10.123 CLEARB     NODE73                                                   0.           F    0.123"


@pytest.fixture
def line_short_circuit_clearing_event_record() -> str:
    return "  10.123 CLEARL     NODE73   NODE74 3                                                               "


@pytest.fixture
def bad_line_event_record() -> str:
    return "   time  BRANC OP    NODE1-NODE2   -2            1                           0.           F       0."


@pytest.fixture
def incomplete_line_short_circuit_event_record() -> str:
    return "     10. FAULTONL NODE1   -NODE2   -2 FUG           99.       0.     0."


@pytest.fixture
def event_file_parser() -> EurostagEventParser:
    return EurostagEventParser(
        eurostag_event_file=f"{TEST_DATA_FOLDER}/complete_case/complete_case.seq"
    )


@pytest.fixture
def event_file_parser_errors() -> EurostagEventParser:
    return EurostagEventParser(
        eurostag_event_file=f"{TEST_DATA_FOLDER}/complete_case/complete_case_errors.seq"
    )


@pytest.fixture
def complete_case_events() -> List[Event]:
    return [
        LineShortCircuitEvent(
            time=10,
            first_bus_name="NHVA1",
            second_bus_name="NHVA2",
            parallel_id="1",
            fault_position=0.99,
            fault_resistance=Value(value=10, unit=Unit.OHM),
            fault_reactance=Value(value=8, unit=Unit.OHM)
        ),
        BusShortCircuitEvent(
            time=10,
            bus_name="NHVC2",
            fault_resistance=Value(value=5, unit=Unit.OHM),
            fault_reactance=Value(value=0, unit=Unit.OHM)
        ),
        BranchEvent(
            time=10.14,
            first_bus_name="NHVA1",
            second_bus_name="NHVA2",
            parallel_id="1",
            breaker_position=BreakerPosition.FIRST_BUS,
            breaker_closed=False
        ),
        BranchEvent(
            time=10.14,
            first_bus_name="NHVA1",
            second_bus_name="NHVA2",
            parallel_id="1",
            breaker_position=BreakerPosition.SECOND_BUS,
            breaker_closed=False
        ),
        BreakerEvent(
            time=10.14,
            first_bus_name="NHV A3",
            second_bus_name="NHVA4",
            parallel_id="1",
            breaker_closed=False
        )
    ]
