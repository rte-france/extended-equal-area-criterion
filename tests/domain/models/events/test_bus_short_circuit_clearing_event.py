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
from deeac.domain.models.events import BusShortCircuitClearingEvent, BusShortCircuitEvent
from deeac.domain.exceptions import ElementNotFoundException


class TestBusShortCircuitClearingEvent:

    def test_repr(self, bus_short_circuit_clearing_event_dto):
        event = BusShortCircuitClearingEvent.create_event(bus_short_circuit_clearing_event_dto)
        assert repr(event) == "Bus short-circuit clearing event: Bus=[BUS1]"

    def test_create_event(self, bus_short_circuit_clearing_event_dto):
        event = BusShortCircuitClearingEvent.create_event(bus_short_circuit_clearing_event_dto)
        assert event.bus_name == "BUS1"

    def test_apply_to_network(self, breaker_case_network):
        network = deepcopy(breaker_case_network)

        # Create a short-circuit
        short_circuit = BusShortCircuitEvent("NGENA1")
        short_circuit.apply_to_network(network)
        failed_bus = network.get_bus("NGENA1")
        assert len(failed_bus.loads) == 1
        load = failed_bus.loads[-1]
        assert isinstance(load, FictiveLoad)

        # Clear fault
        clearing = BusShortCircuitClearingEvent("NGENA1")
        clearing.apply_to_network(network)
        assert len(failed_bus.loads) == 0

        # Applying twice does not change anything
        clearing.apply_to_network(network)
        assert len(failed_bus.loads) == 0

        # Bad node name
        clearing = BusShortCircuitClearingEvent("NODE")
        with pytest.raises(ElementNotFoundException):
            clearing.apply_to_network(network)
