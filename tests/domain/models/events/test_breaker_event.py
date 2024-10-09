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

from deeac.domain.models.events import (
    BreakerEvent, BusShortCircuitEvent, BranchEvent, BreakerPosition, LineShortCircuitEvent
)
from deeac.domain.exceptions import ElementNotFoundException, ParallelException


class TestBreakerEvent:

    def test_repr(self, breaker_event_dto):
        event = BreakerEvent.create_event(breaker_event_dto)
        assert repr(event) == (
            "Breaker event: Buses=[BUS1, BUS2] Parallel ID=[1] Breaker closed=[False]"
        )

    def test_create_event(self, breaker_event_dto):
        event = BreakerEvent.create_event(breaker_event_dto)
        assert event.first_bus_name == "BUS1"
        assert event.second_bus_name == "BUS2"
        assert event.parallel_id == "1"
        assert not event.breaker_closed

    def test_apply_to_network(self, breaker_case_network):
        network = deepcopy(breaker_case_network)

        # Breaker not in network
        breaker_event = BreakerEvent("B1", "B2", "2", False)
        with pytest.raises(ElementNotFoundException):
            breaker_event.apply_to_network(network)

        # No element at this parallel index in branch
        breaker_event = BreakerEvent("NHVD1", "NHVD2", "10", False)
        with pytest.raises(ParallelException):
            breaker_event.apply_to_network(network)

        # Check original state of breaker
        breaker = network.breakers[0]
        assert breaker.first_bus.name == "NHVD1"
        assert breaker.second_bus.name == "NHVD2"
        assert breaker.closed

        # Simplify network to merge coupled buses
        simplified_network, _ = network.get_simplified_network()
        assert len(simplified_network.buses) == 16
        assert simplified_network.buses[6].name == "NHVD1_NHVD2"

        # Open breaker
        breaker_event = BreakerEvent("NHVD1", "NHVD2", "1", False)
        breaker_event.apply_to_network(network)
        breaker_event = BreakerEvent("NHVD1", "NHVD2", "2", False)
        breaker_event.apply_to_network(network)
        assert not breaker.closed

        # Simplify network to merge coupled buses
        simplified_network, _ = network.get_simplified_network()
        assert len(simplified_network.buses) == 17
        assert simplified_network.buses[6].name == "NHVD1"
        assert simplified_network.buses[11].name == "NHVD2"

        # Close the breakers
        breaker_event = BreakerEvent("NHVD2", "NHVD1", "1", True)
        breaker_event.apply_to_network(network)
        assert breaker.closed

        # Simplify network to merge coupled buses
        simplified_network, _ = network.get_simplified_network()
        assert len(simplified_network.buses) == 16
        assert simplified_network.buses[6].name == "NHVD1_NHVD2"

        # Test with coupled buses
        network = deepcopy(breaker_case_network)
        short_circuit = BusShortCircuitEvent("NHVD1")
        short_circuit.apply_to_network(network)
        # Check fictive loads on NHVD1 and NHVD2
        load_names = {load.name for load in network.get_bus("NHVD1").loads}
        assert "FICT_LOAD_NHVD1" in load_names
        load_names = {load.name for load in network.get_bus("NHVD2").loads if load.name.startswith("FICT_LOAD")}
        assert not load_names
        # Simplify network to merge coupled buses
        simplified_network, _ = network.get_simplified_network()
        assert len(simplified_network.buses) == 16
        assert simplified_network.buses[6].name == "NHVD1_NHVD2"
        # Check fictive loads on NHVD1 and NHVD2 (same loads as merged)
        load_names = {load.name for load in simplified_network.get_bus("NHVD1").loads}
        assert "FICT_LOAD_NHVD1" in load_names
        load_names = {load.name for load in simplified_network.get_bus("NHVD2").loads}
        assert "FICT_LOAD_NHVD1" in load_names

        # Couple NHVD3 to NHVD2
        breaker_event = BreakerEvent("NHVD2", "NHVD3", "1", True)
        breaker_event.apply_to_network(network)
        load_names = {load.name for load in network.get_bus("NHVD3").loads if load.name.startswith("FICT_LOAD")}
        assert not load_names
        simplified_network, _ = network.get_simplified_network()
        assert len(simplified_network.buses) == 15
        load_names = {load.name for load in simplified_network.get_bus("NHVD3").loads}
        assert "FICT_LOAD_NHVD1" in load_names

        # Uncouple NHVD2 from NHVD1
        breaker_event = BreakerEvent("NHVD2", "NHVD1", "1", False)
        breaker_event.apply_to_network(network)
        simplified_network, _ = network.get_simplified_network()
        # NHVD3 is not short-circuited anymore
        assert len(simplified_network.buses) == 16
        load_names = {load.name for load in simplified_network.get_bus("NHVD3").loads}
        assert load_names == {"CONV_01"}
        # NHVD2 is not short-circuited anymore
        load_names = {load.name for load in simplified_network.get_bus("NHVD2").loads}
        assert load_names == {"CONV_01"}

        # Recouple NHVD2 to NHVD1 and open line between NHVD1 and NHVB1
        breaker_event = BreakerEvent("NHVD2", "NHVD1", "1", True)
        breaker_event.apply_to_network(network)
        opening_event = BranchEvent("NHVB1", "NHVD1", "1", BreakerPosition.SECOND_BUS, False)
        opening_event.apply_to_network(network)
        simplified_network, _ = network.get_simplified_network()
        assert len(simplified_network.buses) == 15
        load_names = {load.name for load in simplified_network.get_bus("NHVD3").loads}
        assert "FICT_LOAD_NHVD1" in load_names
        load_names = {load.name for load in simplified_network.get_bus("NHVD2").loads}
        assert "FICT_LOAD_NHVD1" in load_names

        # Create a short-circuit on line between NHVD2 and NHVB1
        short_circuit = LineShortCircuitEvent("NHVD2", "NHVB1", "1", 0.5)
        short_circuit.apply_to_network(network)
        load_names = {load.name for load in network.get_bus("NHVB1").loads if load.name.startswith("FICT_LOAD")}
        assert load_names == {"FICT_LOAD_1_NHVD2_NHVB1"}
        load_names = {load.name for load in network.get_bus("NHVD2").loads if load.name.startswith("FICT_LOAD")}
        assert load_names == {"FICT_LOAD_1_NHVB1_NHVD2"}
        load_names = {load.name for load in network.get_bus("NHVD1").loads if load.name.startswith("FICT_LOAD")}
        assert load_names == {"FICT_LOAD_NHVD1"}
        simplified_network, _ = network.get_simplified_network()
        load_names = {
            load.name for load in simplified_network.get_bus("NHVD1").loads if load.name.startswith("FICT_LOAD")
        }
        assert load_names == {"FICT_LOAD_NHVD1", "FICT_LOAD_1_NHVB1_NHVD2"}
        load_names = {
            load.name for load in simplified_network.get_bus("NHVB1").loads if load.name.startswith("FICT_LOAD")
        }
        assert load_names == {"FICT_LOAD_1_NHVD2_NHVB1"}

        # Uncouple NHVD1 from NHVD2
        breaker_event = BreakerEvent("NHVD1", "NHVD2", "1", False)
        breaker_event.apply_to_network(network)
        simplified_network, _ = network.get_simplified_network()
        load_names = {load.name for load in network.get_bus("NHVD1").loads if load.name.startswith("FICT_LOAD")}
        assert load_names == {"FICT_LOAD_NHVD1"}
        load_names = {
            load.name for load in simplified_network.get_bus("NHVD1").loads if load.name.startswith("FICT_LOAD")
        }
        assert load_names == {"FICT_LOAD_NHVD1"}
        load_names = {
            load.name for load in simplified_network.get_bus("NHVB1").loads if load.name.startswith("FICT_LOAD")
        }
        assert load_names == {"FICT_LOAD_1_NHVD2_NHVB1"}
