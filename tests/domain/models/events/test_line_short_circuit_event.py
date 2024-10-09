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
from copy import deepcopy

from deeac.domain.models import FictiveLoad, Value, Unit
from deeac.domain.models.events import LineShortCircuitEvent
from deeac.domain.exceptions import ElementNotFoundException, ParallelException, UnexpectedBranchElementException


class TestLineShortCircuitEvent:

    def test_repr(self, line_short_circuit_event_dto):
        event = LineShortCircuitEvent.create_event(line_short_circuit_event_dto)
        assert repr(event) == (
            "Line short circuit: Branch=[BUS1, BUS2] Parallel ID=[1] Position=[0.01] R=[3.0 ohm] X=[0.0 ohm]"
        )

    def test_create_event(self, line_short_circuit_event_dto):
        event = LineShortCircuitEvent.create_event(line_short_circuit_event_dto)
        assert event.first_bus_name == "BUS1"
        assert event.second_bus_name == "BUS2"
        assert event.parallel_id == "1"
        assert event.fault_position == 0.01
        assert event.fault_resistance == Value(3, Unit.OHM)
        assert event.fault_reactance == Value(0, Unit.OHM)

    def test_get_nearest_bus(self, breaker_case_network):
        # Fault near first bus
        short_circuit = LineShortCircuitEvent("NHVA1", "NHVA3", "1", 0.2)
        nearest_bus = next(bus for bus in breaker_case_network.buses if bus.name == "NHVA1")
        assert short_circuit.get_nearest_bus(breaker_case_network) == nearest_bus

        # Fault near second bus
        short_circuit = LineShortCircuitEvent("NHVA1", "NHVA3", "1", 0.6)
        nearest_bus = next(bus for bus in breaker_case_network.buses if bus.name == "NHVA3")
        assert short_circuit.get_nearest_bus(breaker_case_network) == nearest_bus

        # If fault occurs in the middle of the line, first bus is always returned
        short_circuit = LineShortCircuitEvent("NHVA1", "NHVA3", "1", 0.5)
        nearest_bus = next(bus for bus in breaker_case_network.buses if bus.name == "NHVA1")
        assert short_circuit.get_nearest_bus(breaker_case_network) == nearest_bus

    def test_apply_to_network(self, breaker_case_network):
        network = deepcopy(breaker_case_network)
        network2 = deepcopy(breaker_case_network)

        # Branch not in network
        short_circuit = LineShortCircuitEvent("B1", "B2", "2", 0.5)
        with pytest.raises(ElementNotFoundException):
            short_circuit.apply_to_network(network)

        # No element at this parallel index in branch
        short_circuit = LineShortCircuitEvent("NHVC2", "NHVB1", "10", 0.5)
        with pytest.raises(ParallelException):
            short_circuit.apply_to_network(network)

        # Element is a transformer, not a line
        short_circuit = LineShortCircuitEvent("NGENA1", "NHVA1", "1", 0.5)
        with pytest.raises(UnexpectedBranchElementException):
            short_circuit.apply_to_network(network)

        # Branch with a single line
        short_circuit = LineShortCircuitEvent("NHVA1", "NHVA3", "1", 0.2)
        short_circuit.apply_to_network(network)
        # Check if same result if order of supplied buses is not the same
        short_circuit = LineShortCircuitEvent("NHVA3", "NHVA1", "1", 0.8)
        short_circuit.apply_to_network(network2)

        for net in (network, network2):
            failed_branch = net.get_branch("NHVA1", "NHVA3")
            # Check line is opened
            assert not failed_branch["1"].closed
            assert failed_branch["1"].metal_short_circuited
            # Bus NHVA1
            loads = failed_branch.first_bus.loads
            assert len(loads) == 3
            assert isinstance(loads[-1], FictiveLoad)
            # Fault is at a distance of 20% from NHVA1
            assert cmath.isclose(loads[-1].admittance, 19.75500376199855 - 217.0201134431091j, abs_tol=10e-9)
            # Bus NHVA3
            loads = failed_branch.second_bus.loads
            assert len(loads) == 1
            assert isinstance(loads[0], FictiveLoad)
            # Fault is at a distance of 80% from NHVA1
            assert cmath.isclose(loads[-1].admittance, 4.938750940499638 - 54.255028360777274j, abs_tol=10e-9)

        # Branch with two lines
        short_circuit = LineShortCircuitEvent("NHVC2", "NHVB1", "2", 0.3)
        failed_branch = network.get_branch("NHVC2", "NHVB1")
        failed_line_admittance = failed_branch["1"].admittance
        short_circuit.apply_to_network(network)
        # New event to check that event on opened line returns an error
        with pytest.raises(IOError) as e:
            short_circuit.apply_to_network(network)
        assert str(e.value) == "Event happening to a disconnected line, cancelling execution"
        # Check branch is closed but second line opened
        assert failed_branch.closed
        assert failed_branch["1"].closed
        assert not failed_branch["1"].metal_short_circuited
        assert not failed_branch["2"].closed
        assert failed_branch["2"].metal_short_circuited
        # Bus NHVC2
        loads = failed_branch.first_bus.loads
        assert len(loads) == 2
        assert isinstance(loads[-1], FictiveLoad)
        # Fault is at a distance of 30% from NHVC2
        assert cmath.isclose(loads[-1].admittance, failed_line_admittance / 0.3, abs_tol=10e-9)
        # Bus NHVB1
        loads = failed_branch.second_bus.loads
        assert len(loads) == 2
        assert not isinstance(loads[0], FictiveLoad)
        assert isinstance(loads[-1], FictiveLoad)
        # Fault is at a distance of 30% from NHVC2
        assert cmath.isclose(loads[-1].admittance, failed_line_admittance / 0.7, abs_tol=10e-9)

        # Add fault on second line
        short_circuit = LineShortCircuitEvent("NHVC2", "NHVB1", "1", 0.5)
        short_circuit.apply_to_network(network)
        assert not failed_branch.closed
        assert failed_branch["1"].metal_short_circuited
        # Bus NHVC2
        loads = failed_branch.first_bus.loads
        assert len(loads) == 3
        assert loads[1].name == "FICT_LOAD_2_NHVB1_NHVC2"
        assert cmath.isclose(loads[1].admittance, failed_line_admittance / 0.3, abs_tol=10e-9)
        assert loads[2].name == "FICT_LOAD_1_NHVB1_NHVC2"
        assert isinstance(loads[-1], FictiveLoad)
        # Fault is at a distance of 50% from NHVC2
        assert cmath.isclose(loads[-1].admittance, failed_line_admittance / 0.5, abs_tol=10e-9)
        # Bus NHVB1
        loads = failed_branch.second_bus.loads
        assert len(loads) == 3
        assert loads[1].name == "FICT_LOAD_2_NHVC2_NHVB1"
        assert cmath.isclose(loads[1].admittance, failed_line_admittance / 0.7, abs_tol=10e-9)
        assert loads[2].name == "FICT_LOAD_1_NHVC2_NHVB1"
        assert isinstance(loads[-1], FictiveLoad)
        # Fault is at a distance of 50% from NHVC2
        assert cmath.isclose(loads[-1].admittance, failed_line_admittance / 0.5, abs_tol=10e-9)

        # Fault on two branches
        short_circuit1 = LineShortCircuitEvent("NHVC1", "NHVCEQ", "1", 0.5)
        short_circuit2 = LineShortCircuitEvent("NHVC2", "NHVCEQ", "1", 0.5)
        short_circuit1.apply_to_network(network)
        short_circuit2.apply_to_network(network)
        # Check that two loads were added to NHVCEQ
        failed_branch = network.get_branch("NHVC1", "NHVCEQ")
        bus = failed_branch.second_bus
        assert len(bus.loads) == 3
        assert bus.loads[1].name == "FICT_LOAD_1_NHVC1_NHVCEQ"
        assert bus.loads[2].name == "FICT_LOAD_1_NHVC2_NHVCEQ"
        # Fault is at a distance of 50% from NHVC1 and NHVC2
        y_1_eq = 32 - 176j
        y_2_eq = 8.196721311475411 - 90.16393442622952j
        assert cmath.isclose(bus.loads[1].admittance, y_1_eq, abs_tol=10e-9)
        assert cmath.isclose(bus.loads[2].admittance, y_2_eq, abs_tol=10e-9)
        bus = failed_branch.first_bus
        assert cmath.isclose(bus.loads[-1].admittance, y_1_eq, abs_tol=10e-9)
        bus = network.get_branch("NHVC2", "NHVCEQ").first_bus
        assert [load.name for load in bus.loads] == [
            "NHVC2",
            "FICT_LOAD_2_NHVB1_NHVC2",
            "FICT_LOAD_1_NHVB1_NHVC2",
            "FICT_LOAD_1_NHVCEQ_NHVC2"
        ]
        assert cmath.isclose(bus.loads[-1].admittance, y_2_eq, abs_tol=10e-9)
