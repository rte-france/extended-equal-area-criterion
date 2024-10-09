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
from deeac.domain.models.events import LineShortCircuitEvent, BusShortCircuitEvent, BranchEvent, BreakerPosition
from deeac.domain.exceptions import ElementNotFoundException, ParallelException


class TestBranchEvent:

    def test_repr(self, branch_event_dto):
        event = BranchEvent.create_event(branch_event_dto)
        assert repr(event) == (
            "Branch event: Branch=[BUS1, BUS2] Parallel ID=[1] Breaker position=[FIRST_BUS] Breaker closed=[True]"
        )

    def test_create_event(self, branch_event_dto):
        event = BranchEvent.create_event(branch_event_dto)
        assert event.first_bus_name == "BUS1"
        assert event.second_bus_name == "BUS2"
        assert event.parallel_id == "1"
        assert event.breaker_position == BreakerPosition.FIRST_BUS
        assert event.breaker_closed

    def test_apply_to_network(self, breaker_case_network):
        network = deepcopy(breaker_case_network)

        # Branch not in network
        opening_event = BranchEvent("B1", "B2", "2", BreakerPosition.FIRST_BUS, False)
        with pytest.raises(ElementNotFoundException):
            opening_event.apply_to_network(network)

        # No element at this parallel index in branch
        opening_event = BranchEvent("NHVC2", "NHVB1", "10", BreakerPosition.FIRST_BUS, False)
        with pytest.raises(ParallelException):
            opening_event.apply_to_network(network)

        # Branch with a single line
        short_circuit = LineShortCircuitEvent("NHVA1", "NHVA3", "1", 0.5)
        short_circuit.apply_to_network(network)
        opening_event = BranchEvent("NHVA1", "NHVA3", "1", BreakerPosition.FIRST_BUS, False)
        opening_event.apply_to_network(network)
        opened_branch = network.get_branch("NHVA1", "NHVA3")
        # Check that branch is opened and that fictive load was deleted
        assert not opened_branch["1"].closed_at_first_bus
        assert opened_branch["1"].closed_at_second_bus
        # Bus NHVA1
        loads = opened_branch.first_bus.loads
        assert len(loads) == 2
        for load in loads:
            assert not isinstance(load, FictiveLoad)
        # Bus NHVA3
        loads = opened_branch.second_bus.loads
        assert len(loads) == 1
        assert isinstance(loads[0], FictiveLoad)

        # Open other side
        opening_event = BranchEvent("NHVA1", "NHVA3", "1", BreakerPosition.SECOND_BUS, False)
        opening_event.apply_to_network(network)
        # Check that branch is still opened and that fictive load was deleted on both sides
        assert not opened_branch["1"].closed_at_first_bus
        assert not opened_branch["1"].closed_at_second_bus
        # Bus NHVA1
        loads = opened_branch.first_bus.loads
        assert len(loads) == 2
        for load in loads:
            assert not isinstance(load, FictiveLoad)
        # Bus NHVA3
        loads = opened_branch.second_bus.loads
        assert len(loads) == 0

        # Fault on two branches with opening of both sides of a failed line
        short_circuit1 = LineShortCircuitEvent("NHVC1", "NHVCEQ", "1", 0.5)
        short_circuit2 = LineShortCircuitEvent("NHVC2", "NHVCEQ", "1", 0.5)
        short_circuit1.apply_to_network(network)
        short_circuit2.apply_to_network(network)
        opening_event = BranchEvent("NHVC1", "NHVCEQ", "1", BreakerPosition.FIRST_BUS, False)
        opening_event.apply_to_network(network)
        opening_event = BranchEvent("NHVC1", "NHVCEQ", "1", BreakerPosition.SECOND_BUS, False)
        opening_event.apply_to_network(network)
        # Check that only one ficive load remains on NHVCEQ
        failed_branch = network.get_branch("NHVC1", "NHVCEQ")
        bus = failed_branch.second_bus
        assert len(bus.loads) == 2
        assert bus.loads[0].name == "NHVCEQ"
        assert bus.loads[1].name == "FICT_LOAD_1_NHVC2_NHVCEQ"
        # Check other side
        bus = failed_branch.first_bus
        assert len(bus.loads) == 1
        assert not isinstance(bus.loads[0], FictiveLoad)
        # Check bus of other branch
        failed_branch = network.get_branch("NHVC2", "NHVCEQ")
        bus = failed_branch.first_bus
        assert len(bus.loads) == 2
        assert bus.loads[0].name == "NHVC2"
        assert bus.loads[1].name == "FICT_LOAD_1_NHVCEQ_NHVC2"

        # Check in case of bus fault
        short_circuit = BusShortCircuitEvent("NHVB1")
        short_circuit.apply_to_network(network)
        nhvb1 = network.get_bus("NHVB1")
        assert len(nhvb1.loads) == 2
        assert nhvb1.loads[0].name == "NHVB1"
        fict_load = nhvb1.loads[1]
        assert isinstance(fict_load, FictiveLoad)
        assert fict_load.name == "FICT_LOAD_NHVB1"

        # Check that opening works even if branch is modeled as NHVD1 - NHVB1
        opening_event = BranchEvent("NHVB1", "NHVD1", "1", BreakerPosition.SECOND_BUS, False)
        opening_event.apply_to_network(network)
        branch = network.get_branch("NHVB1", "NHVD1")
        assert branch["1"].closed_at_second_bus  # NHVB1
        assert not branch["1"].closed_at_first_bus  # NHVD1
        opening_event = BranchEvent("NHVD1", "NHVB1", "2", BreakerPosition.FIRST_BUS, False)
        opening_event.apply_to_network(network)
        branch = network.get_branch("NHVD1", "NHVB1")
        assert not branch["2"].closed_at_first_bus  # NHVD1
        assert branch["2"].closed_at_second_bus  # NHVB1
        # Check tha opening did no impact failed bus
        nhvb1 = network.get_bus("NHVB1")
        assert len(nhvb1.loads) == 2
        assert nhvb1.loads[0].name == "NHVB1"
        assert fict_load.name == "FICT_LOAD_NHVB1"

        # Element is a transformer
        opening_event = BranchEvent("NGENA1", "NHVA1", "1", BreakerPosition.FIRST_BUS, False)
        opening_event.apply_to_network(network)
        failed_branch = network.get_branch("NGENA1", "NHVA1")
        assert not failed_branch["1"].closed_at_first_bus
        assert failed_branch["1"].closed_at_second_bus
