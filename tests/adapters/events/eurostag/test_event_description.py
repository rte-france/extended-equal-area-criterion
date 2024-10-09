# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest

from deeac.adapters.events.eurostag.exceptions import EventDataValidationException
from deeac.adapters.events.eurostag.dtos import (
    BreakerOpeningEvent, BreakerPosition, LineShortCircuitEvent, NodeShortCircuitClearingEvent,
    LineShortCircuitClearingEvent
)
from deeac.domain.exceptions import DEEACExceptionList


class TestEventDescription:

    def test_parse_event(
        self, breaker_line_event_description, breaker_line_event_record, bad_line_event_record,
        line_short_circuit_event_description, incomplete_line_short_circuit_event_record,
        bus_short_circuit_clearing_event_description, bus_short_circuit_clearing_event_record,
        line_short_circuit_clearing_event_description, line_short_circuit_clearing_event_record
    ):
        # Complete event
        event_data = breaker_line_event_description.parse_event(breaker_line_event_record)
        assert type(event_data) == BreakerOpeningEvent
        assert event_data.time == 10.13
        assert event_data.sending_node == "NODE1"
        assert event_data.receiving_node == "NODE2"
        assert event_data.parallel_index == "2"
        assert event_data.position == BreakerPosition.SENDING_NODE
        assert event_data.branch_type is None
        assert event_data.first_coupled_node is None
        assert event_data.second_coupled_node is None
        assert event_data.coupling_index is None

        # Bus short-circuit clearing
        event_data = bus_short_circuit_clearing_event_description.parse_event(bus_short_circuit_clearing_event_record)
        assert type(event_data) == NodeShortCircuitClearingEvent
        assert event_data.time == 10.123
        assert event_data.node == "NODE73"

        # Line short-circuit clearing
        event_data = line_short_circuit_clearing_event_description.parse_event(line_short_circuit_clearing_event_record)
        assert type(event_data) == LineShortCircuitClearingEvent
        assert event_data.time == 10.123
        assert event_data.sending_node == "NODE73"
        assert event_data.receiving_node == "NODE74"
        assert event_data.parallel_index == "3"

        # Record with bad format
        with pytest.raises(DEEACExceptionList) as e:
            breaker_line_event_description.parse_event(bad_line_event_record)
        errors = e.value.exceptions
        assert len(errors) == 1

        # Bad time type
        assert isinstance(errors[0], EventDataValidationException)
        assert errors[0].event_record == bad_line_event_record
        assert errors[0].location == ("time",)
        assert errors[0].category == "type_error.float"

        # Incomplete record that is still valid
        event_data = line_short_circuit_event_description.parse_event(incomplete_line_short_circuit_event_record)
        assert type(event_data) == LineShortCircuitEvent
        assert event_data.time == 10.
        assert event_data.sending_node == "NODE1"
        assert event_data.receiving_node == "NODE2"
        assert event_data.parallel_index == "2"
        assert event_data.short_circuit_distance == 99
        assert event_data.resistance == 0
        assert event_data.reactance == 0
