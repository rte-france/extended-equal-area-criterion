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
from deeac.adapters.events.eurostag import EurostagEventParser
from deeac.services import EventLoader
from deeac.domain.models import Value, Unit
from deeac.domain.models.events import (
    FailureEvent, MitigationEvent, LineShortCircuitEvent, BusShortCircuitEvent, BranchEvent, BreakerEvent,
    BreakerPosition
)


@pytest.fixture
def event_loader() -> EventLoader:
    return EventLoader(
        event_parser=EurostagEventParser(
            eurostag_event_file=f"{TEST_DATA_FOLDER}/complete_case/complete_case.seq",
        )
    )


@pytest.fixture
def failure_events() -> List[FailureEvent]:
    return [
        LineShortCircuitEvent(
           "NHVA1", "NHVA2", "1", 0.99, Value(value=10, unit=Unit.OHM), Value(value=8, unit=Unit.OHM)
        ),
        BusShortCircuitEvent("NHVC2", Value(value=5, unit=Unit.OHM), Value(value=0, unit=Unit.OHM))
    ]


@pytest.fixture
def mitigation_events() -> List[MitigationEvent]:
    return [
        BranchEvent("NHVA1", "NHVA2", "1", BreakerPosition.FIRST_BUS, False),
        BranchEvent("NHVA1", "NHVA2", "1", BreakerPosition.SECOND_BUS, False),
        BreakerEvent("NHV A3", "NHVA4", "1", False)
    ]
