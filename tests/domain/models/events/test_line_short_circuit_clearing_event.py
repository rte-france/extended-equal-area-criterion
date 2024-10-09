# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest
from copy import deepcopy

from deeac.domain.models import FictiveLoad
from deeac.domain.models.events import LineShortCircuitClearingEvent, LineShortCircuitEvent
from deeac.domain.exceptions import ParallelException


class TestLineShortCircuitClearingEvent:

    def test_repr(self, line_short_circuit_clearing_event_dto):
        event = LineShortCircuitClearingEvent.create_event(line_short_circuit_clearing_event_dto)
        assert repr(event) == "Line short-circuit clearing event: Branch=[BUS1, BUS2] Parallel ID=[4]"

    def test_create_event(self, line_short_circuit_clearing_event_dto):
        event = LineShortCircuitClearingEvent.create_event(line_short_circuit_clearing_event_dto)
        assert event.first_bus_name == "BUS1"
        assert event.second_bus_name == "BUS2"
        assert event.parallel_id == "4"

    def test_apply_to_network(self, breaker_case_network):
        network = deepcopy(breaker_case_network)

        # Create a short-circuit
        short_circuit = LineShortCircuitEvent("NHVA1", "NHVA3", "1", 0.2)
        short_circuit.apply_to_network(network)
        failed_line = network.get_branch("NHVA1", "NHVA3")["1"]
        assert failed_line.metal_short_circuited
        first_failed_bus = network.get_bus("NHVA1")
        second_failed_bus = network.get_bus("NHVA3")
        assert len(first_failed_bus.loads) == 3
        assert len(second_failed_bus.loads) == 1
        load = first_failed_bus.loads[-1]
        assert isinstance(load, FictiveLoad)
        load = second_failed_bus.loads[-1]
        assert isinstance(load, FictiveLoad)

        # Clear fault
        clearing = LineShortCircuitClearingEvent("NHVA1", "NHVA3", "1")
        clearing.apply_to_network(network)
        assert not failed_line.metal_short_circuited
        assert len(first_failed_bus.loads) == 2
        load = first_failed_bus.loads[-1]
        assert not isinstance(load, FictiveLoad)
        assert len(second_failed_bus.loads) == 0

        # Applying twice does not change anything
        clearing.apply_to_network(network)
        assert len(first_failed_bus.loads) == 2
        assert len(second_failed_bus.loads) == 0

        # Try with other node order
        short_circuit.apply_to_network(network)
        assert failed_line.metal_short_circuited
        assert len(first_failed_bus.loads) == 3
        assert len(second_failed_bus.loads) == 1
        clearing = LineShortCircuitClearingEvent("NHVA3", "NHVA1", "1")
        clearing.apply_to_network(network)
        assert not failed_line.metal_short_circuited
        assert len(first_failed_bus.loads) == 2
        assert len(second_failed_bus.loads) == 0

        # Bad parallel ID
        clearing = LineShortCircuitClearingEvent("NHVA1", "NHVA3", "10")
        with pytest.raises(ParallelException):
            clearing.apply_to_network(network)
