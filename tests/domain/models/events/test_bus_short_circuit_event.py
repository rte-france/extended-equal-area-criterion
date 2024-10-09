# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest
import cmath
import sys
from copy import deepcopy

from deeac.domain.models import FictiveLoad, Value, Unit
from deeac.domain.models.events import BusShortCircuitEvent, LineShortCircuitEvent
from deeac.domain.exceptions import ElementNotFoundException, TransformerImpedanceException


class TestBusShortCircuitEvent:

    def test_repr(self, bus_short_circuit_event_dto):
        event = BusShortCircuitEvent.create_event(bus_short_circuit_event_dto)
        assert repr(event) == "Bus short circuit: Bus=[BUS1] R=[3.0 ohm] X=[0.0 ohm]"

    def test_create_event(self, bus_short_circuit_event_dto):
        event = BusShortCircuitEvent.create_event(bus_short_circuit_event_dto)
        assert event.bus_name == "BUS1"
        assert event.fault_resistance == Value(3, Unit.OHM)
        assert event.fault_reactance == Value(sys.float_info.epsilon, Unit.OHM)

    def test_get_nearest_bus(self, breaker_case_network):
        # Fault at bus NHVA1
        bus = breaker_case_network.get_bus("NHVA1")
        short_circuit = BusShortCircuitEvent("NHVA1")
        assert short_circuit.get_nearest_bus(breaker_case_network) == bus

    def test_apply_to_network(self, breaker_case_network):
        network = deepcopy(breaker_case_network)

        # Bus not in network
        short_circuit = BusShortCircuitEvent("B1")
        with pytest.raises(ElementNotFoundException):
            short_circuit.apply_to_network(network)

        # Bus with a single branch (metal fault)
        short_circuit = BusShortCircuitEvent("NGENA1")
        branch = network.get_branch("NGENA1", "NHVA1")

        # Open transformer without load flow data
        branch["2"].closed_at_first_bus = False
        short_circuit.apply_to_network(network)
        # Bus NHVA1
        loads = branch.second_bus.loads
        assert len(loads) == 2
        for load in loads:
            assert not isinstance(load, FictiveLoad)

        # Bus NGENA1: fictive load with almost infinite admittance
        loads = branch.first_bus.loads
        assert len(loads) == 1
        load = loads[0]
        assert isinstance(load, FictiveLoad)
        first_fault_admittance = load.admittance
        assert cmath.isclose(
            first_fault_admittance,
            1 / complex(sys.float_info.epsilon, 0),
            abs_tol=10e-9
        )

        # Bus with two branches
        short_circuit = BusShortCircuitEvent(bus_name="NHVA3", fault_resistance=Value(100, Unit.OHM))
        # Get failed bus
        failed_bus = network.get_bus("NHVA3")
        # Check load on failed bus
        short_circuit.apply_to_network(network)
        assert len(failed_bus.loads) == 1
        load = failed_bus.loads[0]
        assert isinstance(load, FictiveLoad)
        fault_admittance = load.admittance
        assert cmath.isclose(
            fault_admittance,
            1 / complex(100, sys.float_info.epsilon),
            abs_tol=10e-9
        )
        # Check branches
        branches = failed_bus.branches
        for branch in branches:
            # Get fictive load
            other_bus = branch.first_bus if branch.first_bus != failed_bus else branch.second_bus
            fictive_loads = {load for load in other_bus.loads if isinstance(load, FictiveLoad)}
            assert not fictive_loads

        # Bus already implied in another fault
        short_circuit = BusShortCircuitEvent(bus_name="NHVA1", fault_reactance=Value(200, Unit.OHM))
        short_circuit.apply_to_network(network)
        short_circuit = LineShortCircuitEvent("NHVA1", "NHVA3", "1", 0.5)
        short_circuit.apply_to_network(network)
        # Get failed bus
        failed_bus = network.get_bus("NHVA1")

        assert len(failed_bus.loads) == 4
        # A load was only added on the adjacent buses
        fictive_loads = [load for load in failed_bus.loads if isinstance(load, FictiveLoad)]
        assert len(fictive_loads) == 2
        assert fictive_loads[0].name == "FICT_LOAD_NHVA1"
        assert cmath.isclose(
            fictive_loads[0].admittance,
            1 / complex(sys.float_info.epsilon, 200),
            abs_tol=10e-9
        )
        assert fictive_loads[1].name == "FICT_LOAD_1_NHVA3_NHVA1"

        # Coupled bus NHVD1 and NHVD2
        short_circuit = BusShortCircuitEvent("NHVD1", Value(100, Unit.OHM), Value(200, Unit.OHM))
        short_circuit.apply_to_network(network)
        # Merge buses
        simplified_nework, _ = network.get_simplified_network()
        for bus_name in ["NHVD1", "NHVD2"]:  # Same bus after coupling
            bus = simplified_nework.get_bus(bus_name)
            loads = [load for load in bus.loads if isinstance(load, FictiveLoad)]
            assert len(loads) == 1
            load = loads[0]
            assert load.name == "FICT_LOAD_NHVD1"
            assert cmath.isclose(load.admittance, 1 / complex(100, 200), abs_tol=10e-9)
