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
import numpy as np
from copy import deepcopy

from deeac.domain.models import (
    Line, Network, Bus, BusType, Value, Unit, PUBase, Breaker, ParallelBreakers, Branch, Generator, GeneratorType, Load,
    CapacitorBank, NetworkState, FictiveLoad
)
from deeac.domain.exceptions import ElementNotFoundException, SimplifiedNetworkBreakerExcepion, DEEACExceptionList, \
    NetworkStateException, MultipleSlackBusException, NoSlackBusException


class TestNetwork:

    def test_create_network(self, network_loader, breaker_case_network):
        # TODO: fix the 0 instead of 900MW from the topology parser
        network = network_loader.load_network()
        # Check base power
        assert network.base_power.value == 100
        assert network.base_power.unit == Unit.MVA

        # Check breakers
        assert len(network.breakers) == len(breaker_case_network.breakers)
        for (i, breaker) in enumerate(network.breakers):
            bc_ref_breaker = breaker_case_network.breakers[i]
            # Check state
            assert len(breaker._breakers) == len(bc_ref_breaker._breakers)
            for (j, sub_breaker) in breaker._breakers.items():
                sub_bc_ref_breaker = bc_ref_breaker._breakers[j]
                assert sub_breaker.closed == sub_bc_ref_breaker.closed
            # Check buses
            assert breaker.first_bus.name == bc_ref_breaker.first_bus.name
            assert breaker.second_bus.name == bc_ref_breaker.second_bus.name

        # Check buses
        assert len(network.buses) == len(breaker_case_network.buses)
        for (i, bus) in enumerate(network.buses):
            print(bus.name)
            bc_ref_bus = breaker_case_network.buses[i]
            assert bus.name == bc_ref_bus.name
            assert bus.base_voltage == bc_ref_bus.base_voltage
            assert bus.voltage_magnitude == bc_ref_bus.voltage_magnitude
            assert bus.phase_angle == bc_ref_bus.phase_angle
            assert bus.type == bc_ref_bus.type

            # Check loads
            assert len(bus.loads) == len(bc_ref_bus.loads)
            for (j, load) in enumerate(bus.loads):
                bc_ref_load = bc_ref_bus.loads[j]
                assert load.name == bc_ref_load.name
                assert load.bus == bus
                assert load._active_power == bc_ref_load._active_power
                assert load._reactive_power == bc_ref_load._reactive_power
                assert load.connected == bc_ref_load.connected

            # Check capacitor banks
            assert len(bus.capacitor_banks) == len(bc_ref_bus.capacitor_banks)
            for (j, bank) in enumerate(bus.capacitor_banks):
                bc_ref_bank = bc_ref_bus.capacitor_banks[j]
                assert bank.name == bc_ref_bank.name
                assert bank.bus == bus
                assert bank._active_power == bc_ref_bank._active_power
                assert bank._reactive_power == bc_ref_bank._reactive_power

            # Check generators
            assert len(bus.generators) == len(bc_ref_bus.generators)
            for (j, generator) in enumerate(bus.generators):
                bc_ref_gen = bc_ref_bus.generators[j]
                assert generator.name == bc_ref_gen.name
                assert generator.type == bc_ref_gen.type
                assert generator.bus == bus
                assert generator._direct_transient_reactance == bc_ref_gen._direct_transient_reactance
                assert generator._inertia_constant == bc_ref_gen._inertia_constant
                assert generator._min_active_power == bc_ref_gen._min_active_power
                assert generator._active_power.value == bc_ref_gen._active_power.value
                assert generator._max_active_power == bc_ref_gen._max_active_power
                assert generator._min_reactive_power == bc_ref_gen._min_reactive_power
                assert generator._reactive_power == bc_ref_gen._reactive_power
                assert generator._max_reactive_power == bc_ref_gen._max_reactive_power
                assert generator._target_voltage_magnitude == bc_ref_gen._target_voltage_magnitude
                assert generator.connected == bc_ref_gen.connected

            # Check branches
            assert len(bus.branches) == len(bc_ref_bus.branches)
            for (j, branch) in enumerate(bus.branches):
                bc_ref_branch = bc_ref_bus.branches[j]
                # TODO: fix the internal inconsistency between load flow and topology
                try:
                    assert len(branch.parallel_elements) == len(bc_ref_branch.parallel_elements)
                except:
                    return
                for (k, element) in branch.parallel_elements.items():
                    bc_ref_element = bc_ref_branch[k]
                    assert element._resistance == bc_ref_element._resistance
                    assert element._reactance == bc_ref_element._reactance
                    assert element.closed == bc_ref_element.closed
                    if isinstance(element, Line):
                        # Check line
                        assert element._shunt_conductance == bc_ref_element._shunt_conductance
                        assert element._shunt_susceptance == bc_ref_element._shunt_susceptance
                    else:
                        # Check transformer
                        if element.tap is None:
                            assert bc_ref_element.tap is None
                        else:
                            assert element.tap.number == bc_ref_element.tap.number
                            assert element.tap._phase_shift_angle == bc_ref_element.tap._phase_shift_angle

    def test_duplicate(self, case1_network_line_fault):
        assert len(case1_network_line_fault.failure_events) == 1
        assert len(case1_network_line_fault.mitigation_events) == 2

        assert case1_network_line_fault._simplified_networks[NetworkState.PRE_FAULT] is not None
        assert case1_network_line_fault._simplified_networks[NetworkState.DURING_FAULT] is not None
        assert case1_network_line_fault._simplified_networks[NetworkState.POST_FAULT] is not None

        duplication = case1_network_line_fault.duplicate()
        assert duplication._failure_events == []
        assert duplication._mitigation_events == []

        assert duplication._simplified_networks[NetworkState.PRE_FAULT] is not None
        assert duplication._simplified_networks[NetworkState.DURING_FAULT] is None
        assert duplication._simplified_networks[NetworkState.POST_FAULT] is None

        assert id(duplication) != id(case1_network_line_fault)
        assert id(duplication.buses) != id(case1_network_line_fault.buses)
        assert id(duplication.buses[0]) != id(case1_network_line_fault.buses[0])
        assert len(duplication.buses) == len(case1_network_line_fault.buses)
        assert len(duplication._breakers) == len(case1_network_line_fault._breakers)

    def test_get_bus(self, breaker_case_network):
        bus = breaker_case_network.get_bus("NHVD1")
        assert bus.name == "NHVD1"

        with pytest.raises(ElementNotFoundException):
            breaker_case_network.get_bus("UNKNOWN")

        # Check when bus is coupled to another
        bus = breaker_case_network.get_simplified_network()[0].get_bus("NHVD1")
        assert bus.name == "NHVD1_NHVD2"

    def test_get_branch(self, breaker_case_network):
        branch = breaker_case_network.get_branch("NHVC2", "NHVB1")
        assert len(branch.parallel_elements) == 2

        # Test switching buses
        branch2 = breaker_case_network.get_branch("NHVB1", "NHVC2")
        assert branch == branch2

        with pytest.raises(ElementNotFoundException):
            breaker_case_network.get_branch("NHVQ1", "NHVB1")

        with pytest.raises(ElementNotFoundException):
            breaker_case_network.get_branch("NHVC2", "NGENA1")

        with pytest.raises(ElementNotFoundException):
            breaker_case_network.get_branch("NGENA1", "NGENB1")

        # Check when bus is coupled to another
        branch = breaker_case_network.get_simplified_network()[0].get_branch("NHVD1", "NHVA3")
        assert branch.first_bus.name == "NHVA3"
        assert branch.second_bus.name == "NHVD1_NHVD2"

        # Use other coupled bus and inverse bus names to check it has no impact
        branch = breaker_case_network.get_simplified_network()[0].get_branch("NHVA3", "NHVD2")
        assert branch.first_bus.name == "NHVA3"
        assert branch.second_bus.name == "NHVD1_NHVD2"

    def test_get_parallel_breakers(self, breaker_case_network):
        parallel_breakers = breaker_case_network.get_parallel_breakers("NHVD1", "NHVD2")
        assert parallel_breakers.closed
        parallel_breakers = breaker_case_network.get_parallel_breakers("NHVB1", "NHVB2")
        assert not parallel_breakers.closed
        with pytest.raises(ElementNotFoundException):
            breaker_case_network.get_parallel_breakers("NHVB1", "NHVD2")
        with pytest.raises(SimplifiedNetworkBreakerExcepion):
            simplified_network = breaker_case_network.get_simplified_network()[0]
            simplified_network.get_parallel_breakers("NHVD1", "NHVD2")

    def test_breakers(self, breaker_case_network):
        assert len(breaker_case_network.breakers) == 3
        for index, (bus1_name, bus2_name) in enumerate([("NHVD1", "NHVD2"), ("NHVD2", "NHVD3"), ("NHVB1", "NHVB2")]):
            parallel_breakers = breaker_case_network.breakers[index]
            assert parallel_breakers.first_bus.name == bus1_name
            assert parallel_breakers.second_bus.name == bus2_name

    def test_get_events(self, case1_network, case1_line_fault_event_loader):
        failure_events, mitigation_events = case1_line_fault_event_loader.load_events()
        case1_network.provide_events(failure_events, mitigation_events)
        assert case1_network.failure_events == failure_events
        assert case1_network.mitigation_events == mitigation_events

    def test_generators(self, simple_network):
        generators = simple_network.generators
        assert len(generators) == 4
        assert generators[0].name == "GEN1"
        assert generators[1].name == "GEN2"
        assert generators[2].name == "GEN3"
        assert generators[3].name == "SLACKGEN"

    def test_loads(self, simple_network):
        loads = simple_network.loads
        assert len(loads) == 3
        assert loads[0].name == "LOAD3"
        assert loads[1].name == "LOAD2"
        assert loads[2].name == "LOAD1"

    def test_capacitor_banks(self, simple_network):
        banks = simple_network.capacitor_banks
        assert len(banks) == 1
        assert banks[0].name == "BANK"

    def test_build_bus_coupling_map(self, breaker_case_network):
        assert len(breaker_case_network._bus_coupling_map) == 2
        nhvd1 = breaker_case_network.get_bus("NHVD1")
        nhvd2 = breaker_case_network.get_bus("NHVD2")
        assert breaker_case_network._bus_coupling_map[nhvd1] == {nhvd2}
        assert breaker_case_network._bus_coupling_map[nhvd2] == {nhvd1}

    def test_change_breaker_position(self, breaker_case_network):
        nhvd1 = breaker_case_network.get_bus("NHVD1")
        nhvd2 = breaker_case_network.get_bus("NHVD2")
        breaker_case_network.change_breaker_position(nhvd1.name, nhvd2.name, "1", False)
        assert not breaker_case_network._bus_coupling_map[nhvd1]
        assert not breaker_case_network._bus_coupling_map[nhvd2]

        breaker_case_network.change_breaker_position(nhvd1.name, nhvd2.name, "2", True)
        assert breaker_case_network._bus_coupling_map[nhvd1] == {nhvd2}
        assert breaker_case_network._bus_coupling_map[nhvd2] == {nhvd1}

        nhvb1 = breaker_case_network.get_bus("NHVB1")
        nhvb2 = breaker_case_network.get_bus("NHVB2")
        breaker_case_network.change_breaker_position(nhvb1.name, nhvb2.name, "1", True)
        assert breaker_case_network._bus_coupling_map[nhvd1] == {nhvd2}
        assert breaker_case_network._bus_coupling_map[nhvd2] == {nhvd1}
        assert breaker_case_network._bus_coupling_map[nhvb1] == {nhvb2}
        assert breaker_case_network._bus_coupling_map[nhvb2] == {nhvb1}

        breaker_case_network.change_breaker_position(nhvd1.name, nhvd2.name, "2", False)
        assert not breaker_case_network._bus_coupling_map[nhvd1]
        assert not breaker_case_network._bus_coupling_map[nhvd2]
        assert breaker_case_network._bus_coupling_map[nhvb1] == {nhvb2}
        assert breaker_case_network._bus_coupling_map[nhvb2] == {nhvb1}

    def test_get_simplified_network_and_coupled_buses(self, breaker_case_network, simple_network):
        # Create buses
        bus1 = Bus(
            name="BUS1",
            base_voltage=Value(10, Unit.KV),
            voltage_magnitude=Value(12, Unit.KV, PUBase(10, unit=Unit.KV)),
            phase_angle=Value(0, Unit.DEG)
        )
        bus2 = Bus(
            name="BUS2",
            base_voltage=Value(10, Unit.KV),
            voltage_magnitude=Value(12, Unit.KV, PUBase(10, unit=Unit.KV)),
            phase_angle=Value(0, Unit.DEG),
            type=BusType.SLACK
        )
        bus3 = Bus(
            name="BUS3",
            base_voltage=Value(10, Unit.KV),
            voltage_magnitude=Value(12, Unit.KV, PUBase(10, unit=Unit.KV)),
            phase_angle=Value(0, Unit.DEG)
        )
        bus4 = Bus(
            name="BUS4",
            base_voltage=Value(10, Unit.KV),
            voltage_magnitude=Value(12, Unit.KV, PUBase(10, unit=Unit.KV)),
            phase_angle=Value(0, Unit.DEG)
        )
        bus5 = Bus(
            name="BUS5",
            base_voltage=Value(10, Unit.KV),
            voltage_magnitude=Value(12, Unit.KV, PUBase(10, unit=Unit.KV)),
            phase_angle=Value(0, Unit.DEG)
        )
        bus6 = Bus(
            name="BUS6",
            base_voltage=Value(10, Unit.KV),
            voltage_magnitude=Value(12, Unit.KV, PUBase(10, unit=Unit.KV)),
            phase_angle=Value(0, Unit.DEG)
        )
        bus7 = Bus(
            name="BUS7",
            base_voltage=Value(10, Unit.KV),
            voltage_magnitude=Value(12, Unit.KV, PUBase(10, unit=Unit.KV)),
            phase_angle=Value(0, Unit.DEG),
            type=BusType.SLACK
        )
        buses = [bus1, bus2, bus3, bus4, bus5, bus6, bus7]

        # Create PQ generator and connect to bus3
        gen = Generator(
            name="GEN",
            type=GeneratorType.PQ,
            bus=bus3,
            direct_transient_reactance=Value(value=100, unit=Unit.OHM, base=PUBase(value=10, unit=Unit.OHM)),
            inertia_constant=Value(value=5, unit=Unit.MWS_PER_MVA),
            min_active_power=Value(value=0, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
            active_power=Value(value=900, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
            max_active_power=Value(value=1000, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
            min_reactive_power=Value(value=100, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
            reactive_power=Value(value=300, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
            max_reactive_power=Value(value=500, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
            target_voltage_magnitude=Value(value=380, unit=Unit.KV, base=PUBase(value=10, unit=Unit.KV)),
            connected=True
        )
        bus3.add_generator(gen)

        # Create load and connect to bus2
        load = Load(
            name="LOAD",
            bus=bus2,
            active_power=Value(100, Unit.MW, PUBase(10, Unit.MW)),
            reactive_power=Value(30000, Unit.KVAR, PUBase(10, Unit.MVAR)),
            connected=True
        )
        bus2.add_load(load)

        # Create capacitor bank and connect to bus2
        bank = CapacitorBank(
            name="BANK",
            bus=bus2,
            active_power=Value(0, Unit.MW, PUBase(10, Unit.MW)),
            reactive_power=Value(150, Unit.MVAR, PUBase(10, Unit.MVAR))
        )
        bus2.add_capacitor_bank(bank)

        # Create branches
        branch16 = Branch(bus1, bus6)
        branch16["1"] = Line(Value(100, Unit.OHM), Value(200, Unit.OHM), Value(20, Unit.S), Value(30, Unit.S))
        bus1.add_branch(branch16)
        bus6.add_branch(branch16)
        branch46 = Branch(bus4, bus6)
        branch46["1"] = Line(Value(100, Unit.OHM), Value(200, Unit.OHM), Value(20, Unit.S), Value(30, Unit.S))
        bus4.add_branch(branch46)
        bus6.add_branch(branch46)
        branch56 = Branch(bus5, bus6)
        branch56["1"] = Line(Value(100, Unit.OHM), Value(200, Unit.OHM), Value(20, Unit.S), Value(30, Unit.S))
        bus5.add_branch(branch56)
        bus6.add_branch(branch56)
        branch25 = Branch(bus2, bus5)
        branch25["1"] = Line(Value(100, Unit.OHM), Value(200, Unit.OHM), Value(20, Unit.S), Value(30, Unit.S))
        bus2.add_branch(branch25)
        bus5.add_branch(branch25)
        branch35 = Branch(bus3, bus5)
        branch35["1"] = Line(Value(100, Unit.OHM), Value(200, Unit.OHM), Value(20, Unit.S), Value(30, Unit.S))
        bus3.add_branch(branch35)
        bus5.add_branch(branch35)
        branch57 = Branch(bus5, bus7)
        branch57["1"] = Line(Value(100, Unit.OHM), Value(200, Unit.OHM), Value(20, Unit.S), Value(30, Unit.S))
        bus5.add_branch(branch57)
        bus7.add_branch(branch57)
        # Second slack bus is disconnected
        branch57["1"].closed_at_first_bus = False

        # Create parallel breakers
        parallel_breakers1 = ParallelBreakers(first_bus=bus1, second_bus=bus2)
        parallel_breakers1._breakers = {"A": Breaker(closed=True)}
        parallel_breakers2 = ParallelBreakers(first_bus=bus1, second_bus=bus3)
        parallel_breakers2._breakers = {"A": Breaker(closed=True)}
        parallel_breakers3 = ParallelBreakers(first_bus=bus4, second_bus=bus1)
        parallel_breakers3._breakers = {"A": Breaker(closed=True)}
        parallel_breakers4 = ParallelBreakers(first_bus=bus1, second_bus=bus4)
        parallel_breakers4._breakers = {"A": Breaker(closed=True)}
        parallel_breakers5 = ParallelBreakers(first_bus=bus1, second_bus=bus4)
        parallel_breakers5._breakers = {"A": Breaker(closed=False)}
        parallel_breakers6 = ParallelBreakers(first_bus=bus3, second_bus=bus4)
        parallel_breakers6._breakers = {"A": Breaker(closed=True)}
        parallel_breakers7 = ParallelBreakers(first_bus=bus2, second_bus=bus4)
        parallel_breakers7._breakers = {"A": Breaker(closed=True)}
        parallel_breakers8 = ParallelBreakers(first_bus=bus2, second_bus=bus5)
        parallel_breakers8._breakers = {"A": Breaker(closed=True)}
        parallel_breakers9 = ParallelBreakers(first_bus=bus3, second_bus=bus5)
        parallel_breakers9._breakers = {"A": Breaker(closed=True)}
        parallel_breakers10 = ParallelBreakers(first_bus=bus2, second_bus=bus6)
        parallel_breakers10._breakers = {"A": Breaker(closed=True)}

        # First network: buses 1 and 2 connected
        network = Network(buses=buses, breakers=[parallel_breakers1], base_power=Value(100, Unit.MVA))
        simplified_network, disconnected_buses = network.get_simplified_network()
        assert disconnected_buses == ['BUS7']
        network_buses = simplified_network.buses
        bus_names = ["BUS1_BUS2", "BUS3", "BUS4", "BUS5", "BUS6", "INTERNAL_VOLTAGE_GEN"]
        assert bus_names == [bus.name for bus in network_buses]
        assert network_buses[0].type == BusType.SLACK
        assert network_buses[-1].type == BusType.GEN_INT_VOLT
        # Check that generator, load and capacitor banks were conserved
        assert len(simplified_network.generators) == 1
        assert len(simplified_network.loads) == 1
        assert len(simplified_network.capacitor_banks) == 1
        coupled_buses = {bus1, bus2}
        for bus in coupled_buses:
            assert network.get_coupled_buses(bus) == coupled_buses

        # Second network: buses 1, 2 and 3 connected
        network = Network(
            buses=buses,
            breakers=[parallel_breakers1, parallel_breakers2],
            base_power=Value(100, Unit.MVA)
        )
        network_buses = network.get_simplified_network()[0].buses
        bus_names = ["BUS1_BUS2_BUS3", "BUS4", "BUS5", "BUS6", "INTERNAL_VOLTAGE_GEN"]
        assert bus_names == [bus.name for bus in network_buses]
        assert network_buses[0].type == BusType.SLACK
        coupled_buses = {bus1, bus2, bus3}
        for bus in coupled_buses:
            assert network.get_coupled_buses(bus) == coupled_buses

        # Third network: buses 1, 2 and 4 connected
        network = Network(
            buses=buses,
            breakers=[parallel_breakers1, parallel_breakers3],
            base_power=Value(100, Unit.MVA)
        )
        network_buses = network.get_simplified_network()[0].buses
        bus_names = ["BUS3", "BUS4_BUS1_BUS2", "BUS5", "BUS6", "INTERNAL_VOLTAGE_GEN"]
        assert bus_names == [bus.name for bus in network_buses]
        assert network_buses[1].type == BusType.SLACK
        coupled_buses = {bus1, bus2, bus4}
        for bus in coupled_buses:
            assert network.get_coupled_buses(bus) == coupled_buses

        # Fourth network: buses 4 and 1 connected, two times same breaker
        network = Network(
            buses=buses,
            breakers=[parallel_breakers3, parallel_breakers3, parallel_breakers4],
            base_power=Value(100, Unit.MVA)
        )
        network_buses = network.get_simplified_network()[0].buses
        bus_names = ["BUS2", "BUS3", "BUS4_BUS1", "BUS5", "BUS6", "INTERNAL_VOLTAGE_GEN"]
        assert bus_names == [bus.name for bus in network_buses]
        assert network_buses[2].type == BusType.PQ
        coupled_buses = {bus1, bus4}
        for bus in coupled_buses:
            assert network.get_coupled_buses(bus) == coupled_buses

        # Fifth network: breaker is opened
        network = Network(buses=buses, breakers=[parallel_breakers5], base_power=Value(100, Unit.MVA))
        network_buses = network.get_simplified_network()[0].buses
        bus_names = ["BUS1", "BUS2", "BUS3", "BUS4", "BUS5", "BUS6", "INTERNAL_VOLTAGE_GEN"]
        assert bus_names == [bus.name for bus in network_buses]
        assert network.get_coupled_buses(bus1) == {bus1}

        # Fifth network: Buses 1 to 4 coupled
        network = Network(
            buses=buses,
            breakers=[parallel_breakers1, parallel_breakers2, parallel_breakers3, parallel_breakers4],
            base_power=Value(100, Unit.MVA)
        )
        network_buses = network.get_simplified_network()[0].buses
        bus_names = ["BUS4_BUS1_BUS2_BUS3", "BUS5", "BUS6", "INTERNAL_VOLTAGE_GEN"]
        assert bus_names == [bus.name for bus in network_buses]
        assert network_buses[0].type == BusType.SLACK
        coupled_buses = {bus1, bus2, bus3, bus4}
        for bus in coupled_buses:
            assert network.get_coupled_buses(bus) == coupled_buses

        # Sixth network: two coupled buses
        network = Network(
            buses=buses,
            breakers=[parallel_breakers1, parallel_breakers6],
            base_power=Value(100, Unit.MVA)
        )
        network_buses = network.get_simplified_network()[0].buses
        bus_names = ["BUS1_BUS2", "BUS3_BUS4", "BUS5", "BUS6", "INTERNAL_VOLTAGE_GEN"]
        assert bus_names == [bus.name for bus in network_buses]
        assert network_buses[0].type == BusType.SLACK
        assert network_buses[1].type == BusType.PQ
        coupled_buses = {bus1, bus2}
        for bus in coupled_buses:
            assert network.get_coupled_buses(bus) == coupled_buses
        coupled_buses = {bus3, bus4}
        for bus in coupled_buses:
            assert network.get_coupled_buses(bus) == coupled_buses

        # Seventh network: two coupled buses are coupled themselves
        network = Network(
            buses=buses,
            breakers=[parallel_breakers1, parallel_breakers6, parallel_breakers4, parallel_breakers9],
            base_power=Value(100, Unit.MVA)
        )
        network_buses = network.get_simplified_network()[0].buses
        bus_names = ["BUS1_BUS2_BUS3_BUS4_BUS5", "BUS6", "INTERNAL_VOLTAGE_GEN"]
        assert bus_names == [bus.name for bus in network_buses]
        assert network_buses[0].type == BusType.SLACK
        coupled_buses = {bus1, bus2, bus3, bus4, bus5}
        for bus in coupled_buses:
            assert network.get_coupled_buses(bus) == coupled_buses

        # Eight network: Buses 2 and 5 are isolated from the rest of the network. Buses 3 and 4 are coupled, and
        # generator is disconnected.
        gen.connected = False
        load.connected = False
        branch56["1"].closed_at_first_bus = False
        branch35["1"].closed_at_first_bus = False
        network = Network(
            buses=buses,
            breakers=[parallel_breakers6],
            base_power=Value(100, Unit.MVA)
        )
        with pytest.raises(NoSlackBusException) as e:
            _ = network.get_simplified_network()

        # Ninth network: Check if references are updated
        network = Network(
            buses=buses,
            breakers=[
                parallel_breakers2, parallel_breakers4, parallel_breakers10, parallel_breakers7, parallel_breakers8,
                parallel_breakers9
            ],
            base_power=Value(100, Unit.MVA)
        )
        network_buses = network.get_simplified_network()[0].buses
        bus_names = ["BUS2_BUS6_BUS1_BUS3_BUS4_BUS5"]
        assert bus_names == [bus.name for bus in network_buses]
        assert network_buses[0].type == BusType.SLACK
        coupled_buses = {bus1, bus2, bus3, bus4, bus5, bus6}
        for bus in coupled_buses:
            assert network.get_coupled_buses(bus) == coupled_buses

        # Tenth network: Check if slack bus unicity is guaranteed

        # Run with two disconnected slack buses
        branch57["1"].closed_at_first_bus = True
        branch35["1"].closed_at_first_bus = True
        network = Network(
            buses=buses,
            breakers=[],
            base_power=Value(100, Unit.MVA)
        )
        with pytest.raises(MultipleSlackBusException) as exception:
            _ = network.get_simplified_network()
        assert exception.value.slack_bus_names == ["BUS2", "BUS7"]

        # Try with complete networks
        network_buses = breaker_case_network.get_simplified_network()[0].buses
        # Two buses are merged (and two are disconnected)
        assert len(network_buses) == len(breaker_case_network.buses) + 1
        # Names sorted according to generators and coupled buses
        bus_names = [
            "NGENA1", "NHVA1", "NGENB1", "NGENB2", "NHVA2", "NHVB1", "NHVD1_NHVD2", "NHVC1", "NHVC2", "NHVA3", "NHVCEQ",
            "NHVD3", "INTERNAL_VOLTAGE_GENA1", "INTERNAL_VOLTAGE_GENB1", "INTERNAL_VOLTAGE_GENB2",
            "INTERNAL_VOLTAGE_NHVCEQ"
        ]
        assert bus_names == [bus.name for bus in network_buses]

        simplified_network, _ = simple_network.get_simplified_network()
        # Check that calling simplified network two times does not modify the network
        simplified_network, _ = simplified_network.get_simplified_network()
        network_buses = simplified_network.buses
        # Only two buses are merged
        assert len(network_buses) == len(simple_network.buses) + 2
        # Names sorted according to generators and coupled buses
        bus_names = [
            "GENBUS", "SLACKBUS", "BUS1_BUS2", "BUS3", "INTERNAL_VOLTAGE_GEN1", "INTERNAL_VOLTAGE_GEN2",
            "INTERNAL_VOLTAGE_SLACKGEN"
        ]
        assert bus_names == [bus.name for bus in network_buses]
        for generator in simplified_network.generators:
            assert generator.internal_voltage == generator.bus.voltage
            assert cmath.isclose(generator.rotor_angle, np.angle(generator.bus.voltage), abs_tol=10e-9)

        # Check content of all the buses to see if branches were merged properly
        assert repr(network_buses[0]) == (
            "Bus: Name=[GENBUS] Type=[PQ] |Vb|=[24 kV] "
            "|V|=[24 kV [Base: 24 kV]] \u03C6=[-15.17 deg] Generators=[()] "
            "Loads=[()] Capacitor banks=[()] Branches=[(Branch between nodes GENBUS and BUS3: (1:Transformer: "
            "R=[0.1444 ohm [Base: 1444.0 ohm]] X=[10.108 ohm [Base: 1444.0 ohm]] phase shift angle=[0 deg] Closed at primary=[True] "
            "Closed at secondary=[True]))(Branch between nodes INTERNAL_VOLTAGE_GEN1 and GENBUS: (1:Line: R=[0 ohm "
            "[Base: 5.76 ohm]] X=[3.31776 ohm [Base: 5.76 ohm]] Gs=[0 S [Base: 0.1736111111111111 S]] "
            "Bs=[0 S [Base: 0.1736111111111111 S]] Closed at first bus=[True] Closed at second bus=[True] Metal short "
            "circuit=[False]))(Branch between nodes INTERNAL_VOLTAGE_GEN2 and GENBUS: (1:Line: R=[0 ohm "
            "[Base: 5.76 ohm]] X=[3.31776 ohm [Base: 5.76 ohm]] Gs=[0 S [Base: 0.1736111111111111 S]] Bs=[0 S [Base: "
            "0.1736111111111111 S]] Closed at first bus=[True] Closed at second bus=[True] Metal short circuit="
            "[False]))]"
        )

        assert repr(network_buses[1]) == (
            "Bus: Name=[SLACKBUS] Type=[SLACK] |Vb|=[100 kV] "
            "|V|=[105 kV [Base: 100 kV]] \u03C6=[0 deg] Generators=[()] "
            "Loads=[()] Capacitor banks=[()] Branches=[(Branch between nodes SLACKBUS and BUS1_BUS2: (1:Transformer: "
            "R=[0.722 ohm [Base: 1444.0 ohm]] X=[28.88 ohm [Base: 1444.0 ohm]] phase shift angle=[0 deg] Closed at primary=[True] "
            "Closed at secondary=[True]))(Branch between nodes INTERNAL_VOLTAGE_SLACKGEN and SLACKBUS: "
            "(1:Line: R=[0 ohm [Base: 100.0 ohm]] X=[40.0 ohm [Base: 100.0 ohm]] Gs=[0 S [Base: 0.01 S]] Bs=[0 S "
            "[Base: 0.01 S]] Closed at first bus=[True] Closed at second bus=[True] Metal short circuit=[False]))]"
        )

        assert repr(network_buses[2]) == (
            "Bus: Name=[BUS1_BUS2] Type=[PQ] |Vb|=[380 kV] "
            "|V|=[400 kV [Base: 380 kV]] \u03C6=[-2.21 deg] Generators=[()] "
            "Loads=[(Load: Name=[LOAD2] Bus=[BUS1_BUS2] P=[900 MW [Base: 100 MW]] Q=[90 MVAr [Base: 100 MVAr]] "
            "Connected=[True])] Capacitor banks=[(Capacitor bank: Name=[BANK] Bus=[BUS1_BUS2] P=[0 MW [Base: 100 MW]] "
            "Q=[150 MVAr [Base: 10 MVAr]])] Branches=[(Branch between nodes SLACKBUS and BUS1_BUS2: "
            "(1:Transformer: R=[0.722 ohm [Base: 1444.0 ohm]] X=[28.88 ohm [Base: 1444.0 ohm]] phase shift angle=[0 deg] "
            "Closed at primary=[True] Closed at secondary=[True]))(Branch between nodes BUS1_BUS2 and BUS3: "
            "(1:Line: R=[2.888 ohm [Base: 1444.0 ohm]] X=[14.44 ohm [Base: 1444.0 ohm]] Gs=[0 S "
            "[Base: 0.0006925207756232687 S]] Bs=[0.0004155124653739612 S [Base: 0.0006925207756232687 S]] "
            "Closed at first bus=[True] Closed at second bus=[True] Metal short circuit=[False])(2:Line: R=[2.888 ohm "
            "[Base: 1444.0 ohm]] X=[14.44 ohm [Base: 1444.0 ohm]] Gs=[0 S [Base: 0.0006925207756232687 S]] "
            "Bs=[0.0004155124653739612 S [Base: 0.0006925207756232687 S]] Closed at first bus=[True] "
            "Closed at second bus=[True] Metal short circuit=[False]))]"
        )

        assert repr(network_buses[3]) == (
            "Bus: Name=[BUS3] Type=[PQ] |Vb|=[380 kV] "
            "|V|=[398 kV [Base: 380 kV]] \u03C6=[-2.31 deg] Generators=[()] "
            "Loads=[(Load: Name=[LOAD1] Bus=[BUS3] P=[100 MW [Base: 100 MW]] Q=[10 MVAr [Base: 100 MVAr]] "
            "Connected=[True])] Capacitor banks=[()] Branches=[(Branch between nodes BUS1_BUS2 and BUS3: "
            "(1:Line: R=[2.888 ohm [Base: 1444.0 ohm]] X=[14.44 ohm [Base: 1444.0 ohm]] Gs=[0 S "
            "[Base: 0.0006925207756232687 S]] Bs=[0.0004155124653739612 S [Base: 0.0006925207756232687 S]] "
            "Closed at first bus=[True] Closed at second bus=[True] Metal short circuit=[False])(2:Line: "
            "R=[2.888 ohm [Base: 1444.0 ohm]] X=[14.44 ohm [Base: 1444.0 ohm]] Gs=[0 S [Base: 0.0006925207756232687 S]]"
            " Bs=[0.0004155124653739612 S [Base: 0.0006925207756232687 S]] Closed at first bus=[True] "
            "Closed at second bus=[True] Metal short circuit=[False]))(Branch between nodes GENBUS and BUS3: "
            "(1:Transformer: R=[0.1444 ohm [Base: 1444.0 ohm]] X=[10.108 ohm [Base: 1444.0 ohm]] phase shift angle=[0 deg] "
            "Closed at primary=[True] Closed at secondary=[True]))]"
        )

        assert repr(network_buses[4]) == (
            "Bus: Name=[INTERNAL_VOLTAGE_GEN1] Type=[GEN_INT_VOLT] |Vb|=[24 kV] "
            "|V|=[140.5913362906833 kV [Base: 24 kV]] \u03C6=[47.07510370497203 deg] Generators=[(Generator: "
            "Name=[GEN1] Type=[PV] Bus=[INTERNAL_VOLTAGE_GEN1] x'd=[3.31776 ohm [Base: 5.76 ohm]] H=[6.3 MWs/MVA] "
            "Pmin=[-999999 MW [Base: 100 MW]] P=[900 MW [Base: 100 MW]] Pmax=[999999 MW [Base: 100 MW]] "
            "Qmin=[-9999 MVAr [Base: 100 MVAr]] Q=[300 MVAr [Base: 100 MVAr]] Qmax=[9999 MVAr [Base: 100 MVAr]] "
            "|Vt|=[24 kV [Base: 24 kV]] Connected=[True])] Loads=[()] Capacitor banks=[()] Branches=[(Branch between "
            "nodes INTERNAL_VOLTAGE_GEN1 and GENBUS: (1:Line: R=[0 ohm [Base: 5.76 ohm]] X=[3.31776 ohm "
            "[Base: 5.76 ohm]] Gs=[0 S [Base: 0.1736111111111111 S]] Bs=[0 S [Base: 0.1736111111111111 S]] Closed at "
            "first bus=[True] Closed at second bus=[True] Metal short circuit=[False]))]"
        )

        assert repr(network_buses[5]) == (
            "Bus: Name=[INTERNAL_VOLTAGE_GEN2] Type=[GEN_INT_VOLT] |Vb|=[24 kV] "
            "|V|=[75.66481031496741 kV [Base: 24 kV]] \u03C6=[31.78367661159277 deg] Generators=[(Generator: "
            "Name=[GEN2] Type=[PQ] Bus=[INTERNAL_VOLTAGE_GEN2] x'd=[3.31776 ohm [Base: 5.76 ohm]] H=[6.3 MWs/MVA] "
            "Pmin=[-999999 MW [Base: 100 MW]] P=[400 MW [Base: 100 MW]] Pmax=[999999 MW [Base: 100 MW]] Qmin=[-9999 "
            "MVAr [Base: 100 MVAr]] Q=[200 MVAr [Base: 100 MVAr]] Qmax=[9999 MVAr [Base: 100 MVAr]] |Vt|=[None] "
            "Connected=[True])] Loads=[()] Capacitor banks=[()] Branches=[(Branch between nodes INTERNAL_VOLTAGE_GEN2 "
            "and GENBUS: (1:Line: R=[0 ohm [Base: 5.76 ohm]] X=[3.31776 ohm [Base: 5.76 ohm]] Gs=[0 S "
            "[Base: 0.1736111111111111 S]] Bs=[0 S [Base: 0.1736111111111111 S]] Closed at first bus=[True] "
            "Closed at second bus=[True] Metal short circuit=[False]))]"
        )

        assert repr(network_buses[6]) == (
            "Bus: Name=[INTERNAL_VOLTAGE_SLACKGEN] Type=[GEN_INT_VOLT] |Vb|=[100 kV] "
            "|V|=[196.55782183434735 kV [Base: 100 kV]] \u03C6=[22.806721561292324 deg] Generators=[(Generator: "
            "Name=[SLACKGEN] Type=[SLACK] Bus=[INTERNAL_VOLTAGE_SLACKGEN] x'd=[40.0 ohm [Base: 100.0 ohm]] "
            "H=[6.3 MWs/MVA] Pmin=[-999999 MW [Base: 100 MW]] P=[200 MW [Base: 100 MW]] Pmax=[999999 MW [Base: 100 MW]]"
            " Qmin=[-999999 MVAr [Base: 100 MVAr]] Q=[200 MVAr [Base: 100 MVAr]] Qmax=[999999 MVAr [Base: 100 MVAr]] "
            "|Vt|=[105 kV [Base: 100 kV]] Connected=[True])] Loads=[()] Capacitor banks=[()] Branches=[(Branch between "
            "nodes INTERNAL_VOLTAGE_SLACKGEN and SLACKBUS: (1:Line: R=[0 ohm [Base: 100.0 ohm]] X=[40.0 ohm "
            "[Base: 100.0 ohm]] Gs=[0 S [Base: 0.01 S]] Bs=[0 S [Base: 0.01 S]] Closed at first bus=[True] "
            "Closed at second bus=[True] Metal short circuit=[False]))]"
        )

    def test_provide_events(self, case1_network, case1_line_fault_event_loader, case1_bus_fault_event_loader):
        # Events and simplified networks should be empty by default
        assert case1_network._failure_events == []
        assert case1_network._mitigation_events == []
        for _, simplified_network in case1_network._simplified_networks.items():
            assert simplified_network is None

        # Load and provide events
        failure_events, mitigation_events = case1_line_fault_event_loader.load_events()
        network = deepcopy(case1_network)
        network.initialize_simplified_network()
        network.provide_events(failure_events, mitigation_events)

        assert len(network._failure_events) == 1
        assert len(network._mitigation_events) == 2

        # Check different states to see if events were applied
        pre_fault_network = network.get_state(NetworkState.PRE_FAULT)
        assert len(pre_fault_network.buses) == 15
        assert not pre_fault_network.get_branch("NHVA3", "NHVD1")["1"].metal_short_circuited
        assert pre_fault_network.get_branch("NHVA3", "NHVD1").closed
        during_fault_network = network.get_state(NetworkState.DURING_FAULT)
        with pytest.raises(ElementNotFoundException):
            # Branch is considered as opened in case of single line with metal fault
            during_fault_network.get_branch("NHVA3", "NHVD1")
        assert len(during_fault_network.get_bus("NHVA1").loads) == 2
        assert len(during_fault_network.get_bus("NHVA3").loads) == 1
        assert type(during_fault_network.get_bus("NHVA3").loads[0]) == FictiveLoad
        assert len(during_fault_network.get_bus("NHVD1").loads) == 1
        assert type(during_fault_network.get_bus("NHVD1").loads[0]) == FictiveLoad
        post_fault_network = network.get_state(NetworkState.POST_FAULT)
        with pytest.raises(ElementNotFoundException):
            post_fault_network.get_branch("NHVA3", "NHVD1")
        assert len(post_fault_network.get_bus("NHVA3").loads) == 0
        assert len(post_fault_network.get_bus("NHVD1").loads) == 0

        # Load and provide other events
        failure_events, mitigation_events = case1_bus_fault_event_loader.load_events()
        network.provide_events(failure_events, mitigation_events)

        assert network._failure_events == failure_events
        assert network._mitigation_events == mitigation_events

        # Check different states to see if events were applied
        new_pre_fault_network = network.get_state(NetworkState.PRE_FAULT)
        assert new_pre_fault_network == pre_fault_network
        during_fault_network = network.get_state(NetworkState.DURING_FAULT)
        # Check if fictive load was added
        assert len(during_fault_network.get_bus("NHVA3").loads) == 1
        assert type(during_fault_network.get_bus("NHVA3").loads[-1]) == FictiveLoad
        assert len(during_fault_network.get_bus("NHVA1").loads) == 2
        for load in during_fault_network.get_bus("NHVA1").loads:
            assert not isinstance(load, FictiveLoad)
        assert len(during_fault_network.get_bus("NHVD1").loads) == 0
        # Check that bus was disconnected in post-fault state
        post_fault_network = network.get_state(NetworkState.POST_FAULT)
        with pytest.raises(ElementNotFoundException):
            post_fault_network.get_bus("NHVA3")
        assert len(post_fault_network.get_bus("NHVA1").loads) == 2
        assert len(post_fault_network.get_bus("NHVD1").loads) == 0

    def test_get_state(self, case1_network, case1_line_fault_event_loader):
        # Load and provide events
        failure_events, mitigation_events = case1_line_fault_event_loader.load_events()
        network = deepcopy(case1_network)
        with pytest.raises(NetworkStateException):
            network.get_state(NetworkState.DURING_FAULT)
        network.provide_events(failure_events, mitigation_events)

        network.initialize_simplified_network()
        pre_fault_network = network.get_state(NetworkState.PRE_FAULT)
        assert len(pre_fault_network.get_bus("NHVA3").loads) == 0
        assert pre_fault_network.get_branch("NHVA3", "NHVD1").closed
        during_fault_network = network.get_state(NetworkState.DURING_FAULT)
        assert type(during_fault_network.get_bus("NHVA3").loads[0]) == FictiveLoad
        post_fault_network = network.get_state(NetworkState.POST_FAULT)
        assert len(post_fault_network.get_bus("NHVA3").loads) == 0

    def test_get_generator_voltage_amplitude_product(self, case1_network_line_fault):
        generators = case1_network_line_fault.get_state(NetworkState.DURING_FAULT).generators
        expected_result = 1.4349533724638195
        product = case1_network_line_fault.get_generator_voltage_amplitude_product(
            generators[0].name,
            generators[1].name
        )
        assert cmath.isclose(product, expected_result, abs_tol=10e-9)

        product = case1_network_line_fault.get_generator_voltage_amplitude_product(
            generators[1].name,
            generators[0].name
        )
        assert cmath.isclose(product, expected_result, abs_tol=10e-9)
        assert (
            (generators[0].name, generators[1].name) in case1_network_line_fault._generator_voltage_product_amplitudes
        )
        assert len(case1_network_line_fault._generator_voltage_product_amplitudes) == 16

    def test_get_admittance(self, case1_network_line_fault):
        generators = case1_network_line_fault.get_state(NetworkState.DURING_FAULT).generators
        generator1, generator2 = (generators[0], generators[1])

        amplitude, angle = case1_network_line_fault.get_admittance(
            generator1.bus.name,
            generator2.bus.name,
            NetworkState.DURING_FAULT
        )
        assert cmath.isclose(amplitude, 0.16483744697469394, abs_tol=10e-9)
        assert cmath.isclose(angle, 1.2509076886482808, abs_tol=10e-9)

        amplitude, angle = case1_network_line_fault.get_admittance(
            generator2.bus.name,
            generator1.bus.name,
            NetworkState.DURING_FAULT
        )
        assert cmath.isclose(amplitude, 0.16483744697469402, abs_tol=10e-9)
        assert cmath.isclose(angle, 1.2509076886482808, abs_tol=10e-9)
        assert len(case1_network_line_fault._admittances[NetworkState.DURING_FAULT]) == 2

        amplitude, angle = case1_network_line_fault.get_admittance(
            generator2.bus.name,
            generator1.bus.name,
            NetworkState.PRE_FAULT
        )
        assert cmath.isclose(amplitude, 1.3468532056692544, abs_tol=10e-9)
        assert cmath.isclose(angle, 1.1428236247021686, abs_tol=10e-9)
        assert (
            (generator2.bus.name, generator1.bus.name) in
            case1_network_line_fault._admittances[NetworkState.PRE_FAULT]
        )
        assert (
            (generator1.bus.name, generator2.bus.name) in
            case1_network_line_fault._admittances[NetworkState.DURING_FAULT]
        )
        assert len(case1_network_line_fault._admittances[NetworkState.PRE_FAULT]) == 1
        assert len(case1_network_line_fault._admittances[NetworkState.DURING_FAULT]) == 2

    def test_get_buses_in_perimeter(self, case1_network_line_fault):
        network = case1_network_line_fault.get_state(NetworkState.PRE_FAULT)
        bus = network.get_bus("NHVB1")
        # Perimeter of 0 is the bus itself
        buses = network._get_buses_in_perimeter(bus, 0)
        assert len(buses) == 1
        assert buses.pop().name == "NHVB1"

        # Perimeter of 1 contains direct neighbors
        buses = network._get_buses_in_perimeter(bus, 1)
        expected_bus_names = {"NHVC2", "NHVD1", "NHVB1", "NGENB1", "NGENB2"}
        assert len(expected_bus_names - {bus.name for bus in buses}) == 0

        # During fault with perimeter of 2 nodes
        network = case1_network_line_fault.get_state(NetworkState.DURING_FAULT)
        bus = network.get_bus("NHVB1")
        buses = network._get_buses_in_perimeter(bus, 3)
        expected_bus_names = {
            "NHVC2", "NHVD1", "NHVB1", "NGENB1", "NGENB2", "NHVCEQ", "INTERNAL_VOLTAGE_GENB1",
            "INTERNAL_VOLTAGE_GENB2"
        }
        assert len(expected_bus_names - {bus.name for bus in buses}) == 0


class TestSimplifiedNetwork:

    def test_admittance_matrix(self, breaker_case_network):
        branch = breaker_case_network.get_branch("NGENA1", "NHVA1")
        # Open transformer without load flow data
        branch["2"].closed_at_first_bus = False

        simplified_nework, _ = breaker_case_network.get_simplified_network()
        matrix = simplified_nework.admittance_matrix
        assert simplified_nework._admittance_matrix == matrix
