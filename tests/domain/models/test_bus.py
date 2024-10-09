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

from deeac.domain.models import Bus, BusType, Value, Unit, PUBase, Load, CapacitorBank
from deeac.domain.exceptions import BusVoltageException, CoupledBusesException


class TestBus:

    def test_repr(self, simple_bus):
        assert repr(simple_bus) == (
            "Bus: Name=[BUS] Type=[PV] |Vb|=[380 kV] "
            "|V|=[380 kV [Base: 10 kV]] \u03C6=[20 deg] Generators=[(Generator: Name=[GEN] Type=[PV] Bus=[BUS] "
            "x'd=[100 ohm [Base: 10 ohm]] H=[5 MWs/MVA] Pmin=[0 MW [Base: 100 MW]] P=[900 MW [Base: 100 MW]] "
            "Pmax=[1000 MW [Base: 100 MW]] Qmin=[100 MVAr [Base: 100 MVAr]] Q=[300 MVAr [Base: 100 MVAr]] "
            "Qmax=[600 MVAr [Base: 100 MVAr]] |Vt|=[380 kV [Base: 10 kV]] Connected=[True])] "
            "Loads=[(Load: Name=[LOAD] Bus=[BUS] P=[100 MW [Base: 10 MW]] Q=[30000 kVAr [Base: 10 MVAr]] "
            "Connected=[True])] Capacitor banks=[(Capacitor bank: Name=[BANK] Bus=[BUS] P=[0 MW [Base: 10 MW]] "
            "Q=[150 MVAr [Base: 10 MVAr]])] Branches=[(Branch between nodes BUS and BUS3: ())]"
        )

    def test_type(self, simple_bus):
        assert simple_bus.type == BusType.PV
        simple_bus._type = BusType.SLACK
        assert simple_bus.type == BusType.SLACK
        simple_bus._type = BusType.GEN_INT_VOLT
        assert simple_bus.type == BusType.GEN_INT_VOLT
        simple_bus._type = None

    def test_voltage(self, simple_bus):
        assert cmath.isclose(simple_bus.voltage, 35.70831958986452 + 12.996765446375411j, abs_tol=10e-9)
        bus = Bus("BUS", Value(3, Unit.KV))
        with pytest.raises(BusVoltageException) as e:
            bus.voltage
        assert e.value.name == "BUS"

    def test_update_voltage(self, simple_bus):
        assert cmath.isclose(simple_bus.voltage, 35.70831958986452 + 12.996765446375411j, abs_tol=10e-9)
        base = PUBase(10, unit=Unit.KV)
        simple_bus.update_voltage(Value(30, Unit.KV, base), Value(4, Unit.DEG))
        assert cmath.isclose(simple_bus.voltage, 2.9926921507794724 + 0.2092694212323759j, abs_tol=10e-9)
        # Check that internal voltage of generator and admittance of load were updated
        assert cmath.isclose(
            simple_bus.generators[0].internal_voltage,
            10.875638441053956 + 30.83375566646836j,
            abs_tol=10e-9
        )
        assert cmath.isclose(
            simple_bus.loads[0].admittance,
            1.1111111111111116 - 0.3333333333333335j,
            abs_tol=10e-9
        )
        assert cmath.isclose(
            simple_bus.capacitor_banks[0].admittance,
            - 1.6666666666666674j,
            abs_tol=10e-9
        )

    def test_add_generator(self, simple_generator):
        bus = Bus(name="BUS", base_voltage=None)
        assert bus.generators == []
        bus.add_generator(simple_generator)
        assert bus.generators == [simple_generator]

    def test_add_load(self, simple_load):
        bus = Bus(name="BUS", base_voltage=None)
        assert bus.loads == []
        bus.add_load(simple_load)
        assert bus.loads == [simple_load]

    def test_add_capacitor_bank(self, simple_capacitor_bank):
        bus = Bus(name="BUS", base_voltage=None)
        assert bus.capacitor_banks == []
        bus.add_capacitor_bank(simple_capacitor_bank)
        assert bus.capacitor_banks == [simple_capacitor_bank]

    def test_add_branch(self, simple_branch):
        bus = Bus(name="BUS", base_voltage=None)
        assert bus.branches == []
        bus.add_branch(simple_branch)
        assert bus.branches == [simple_branch]

    def test_couple_to_bus(self, simple_bus, simple_bus2):
        cb = deepcopy(simple_bus)
        simple_bus2_copy = deepcopy(simple_bus2)

        # Try to couple to a bus representing a generator internal voltage
        with pytest.raises(CoupledBusesException):
            cb.couple_to_bus(Bus(name="TESTBUS", base_voltage=Value(24, Unit.KV), type=BusType.GEN_INT_VOLT))
        # Try to add a bus without voltage
        with pytest.raises(CoupledBusesException):
            cb.couple_to_bus(Bus(name="TESTBUS", base_voltage=Value(24, Unit.KV)))
        # Try to add a bus with different voltage
        with pytest.raises(CoupledBusesException) as e:
            cb.couple_to_bus(
                Bus(
                    name="TESTBUS",
                    base_voltage=Value(value=100, unit=Unit.KV),
                    voltage_magnitude=Value(value=100, unit=Unit.KV, base=PUBase(value=10, unit=Unit.KV)),
                    phase_angle=Value(value=20, unit=Unit.DEG)
                )
            )
        assert e.value.first_bus_name == simple_bus.name
        assert e.value.second_bus_name == "TESTBUS"

        # Add a bus with same voltage
        cb.couple_to_bus(simple_bus2_copy)
        # Add again same buses to observe if ignored
        cb.couple_to_bus(simple_bus2_copy)
        cb.couple_to_bus(simple_bus)

        # Check references to bus were updated and representation
        assert cb.branches[0].first_bus == cb
        assert cb.branches[1].second_bus == cb
        for gen in cb.generators:
            assert gen.bus == cb
        for load in cb.loads:
            assert load.bus == cb
        for bank in cb.capacitor_banks:
            assert bank.bus == cb
        assert repr(cb) == (
            "Bus: Name=[BUS_BUS2] Type=[SLACK] |Vb|=[380 kV] "
            "|V|=[380 kV [Base: 10 kV]] \u03C6=[20 deg] Generators=[(Generator: Name=[GEN] Type=[PV] Bus=[BUS_BUS2] "
            "x'd=[100 ohm [Base: 10 ohm]] H=[5 MWs/MVA] Pmin=[0 MW [Base: 100 MW]] P=[900 MW [Base: 100 MW]] "
            "Pmax=[1000 MW [Base: 100 MW]] Qmin=[100 MVAr [Base: 100 MVAr]] Q=[300 MVAr [Base: 100 MVAr]] "
            "Qmax=[600 MVAr [Base: 100 MVAr]] |Vt|=[380 kV [Base: 10 kV]] Connected=[True])(Generator: Name=[GEN2] "
            "Type=[PQ] Bus=[BUS_BUS2] x'd=[200 ohm [Base: 10 ohm]] H=[2 MWs/MVA] Pmin=[100 MW [Base: 100 MW]] "
            "P=[300 MW [Base: 100 MW]] Pmax=[900 MW [Base: 100 MW]] Qmin=[0 MVAr [Base: 100 MVAr]] Q=[100 MVAr "
            "[Base: 100 MVAr]] Qmax=[800 MVAr [Base: 100 MVAr]] |Vt|=[380 kV [Base: 10 kV]] Connected=[True])] "
            "Loads=[(Load: Name=[LOAD] Bus=[BUS_BUS2] P=[100 MW [Base: 10 MW]] Q=[30000 kVAr [Base: 10 MVAr]] "
            "Connected=[True])] Capacitor banks=[(Capacitor bank: Name=[BANK] Bus=[BUS_BUS2] P=[0 MW [Base: 10 MW]] "
            "Q=[150 MVAr [Base: 10 MVAr]])] Branches=[(Branch between nodes BUS_BUS2 and BUS3: ())(Branch between "
            "nodes BUS1 and BUS_BUS2: (1:Line: R=[200 ohm [Base: 100 ohm]] X=[3000 ohm [Base: 100 ohm]] Gs=[20 S "
            "[Base: 10 S]] Bs=[30 S [Base: 10 S]] Closed at first bus=[True] Closed at second bus=[True] "
            "Metal short circuit=[False]))]"
        )

        # Create a new bus with a load and a capacitor bank
        bus = Bus(
            name="BUS4",
            base_voltage=Value(value=380, unit=Unit.KV),
            voltage_magnitude=Value(value=380, unit=Unit.KV, base=PUBase(value=10, unit=Unit.KV)),
            phase_angle=Value(value=20, unit=Unit.DEG)
        )
        bus.add_load(
            Load(
                name="LOAD4",
                bus=bus,
                active_power=Value(150, Unit.MW, PUBase(10, Unit.MW)),
                reactive_power=Value(25000, Unit.KVAR, PUBase(10, Unit.MVAR)),
                connected=False
            )
        )
        bus.add_capacitor_bank(
            CapacitorBank(
                name="BANK4",
                bus=bus,
                active_power=Value(10, Unit.MW, PUBase(10, Unit.MW)),
                reactive_power=Value(100, Unit.MVAR, PUBase(10, Unit.MVAR))
            )
        )
        # Add coupled buses to bus created previously
        bus.couple_to_bus(cb)
        bus_repr = (
            "Bus: Name=[BUS4_BUS_BUS2] Type=[SLACK] |Vb|=[380 kV] "
            "|V|=[380 kV [Base: 10 kV]] \u03C6=[20 deg] Generators=[(Generator: Name=[GEN] Type=[PV] "
            "Bus=[BUS4_BUS_BUS2] x'd=[100 ohm [Base: 10 ohm]] H=[5 MWs/MVA] Pmin=[0 MW [Base: 100 MW]] P=[900 MW "
            "[Base: 100 MW]] Pmax=[1000 MW [Base: 100 MW]] Qmin=[100 MVAr [Base: 100 MVAr]] Q=[300 MVAr "
            "[Base: 100 MVAr]] Qmax=[600 MVAr [Base: 100 MVAr]] |Vt|=[380 kV [Base: 10 kV]] Connected=[True])"
            "(Generator: Name=[GEN2] Type=[PQ] Bus=[BUS4_BUS_BUS2] x'd=[200 ohm [Base: 10 ohm]] H=[2 MWs/MVA] "
            "Pmin=[100 MW [Base: 100 MW]] P=[300 MW [Base: 100 MW]] Pmax=[900 MW [Base: 100 MW]] Qmin=[0 MVAr "
            "[Base: 100 MVAr]] Q=[100 MVAr [Base: 100 MVAr]] Qmax=[800 MVAr [Base: 100 MVAr]] |Vt|=[380 kV "
            "[Base: 10 kV]] Connected=[True])] "
            "Loads=[(Load: Name=[LOAD4] Bus=[BUS4_BUS_BUS2] P=[150 MW [Base: 10 MW]] Q=[25000 kVAr [Base: 10 MVAr]] "
            "Connected=[False])(Load: Name=[LOAD] Bus=[BUS4_BUS_BUS2] P=[100 MW [Base: 10 MW]] Q=[30000 kVAr [Base: "
            "10 MVAr]] Connected=[True])] Capacitor banks=[(Capacitor bank: Name=[BANK4] Bus=[BUS4_BUS_BUS2] P=[10 MW "
            "[Base: 10 MW]] Q=[100 MVAr [Base: 10 MVAr]])(Capacitor bank: Name=[BANK] Bus=[BUS4_BUS_BUS2] P=[0 MW "
            "[Base: 10 MW]] Q=[150 MVAr [Base: 10 MVAr]])] Branches=[(Branch between nodes BUS4_BUS_BUS2 and BUS3: ())"
            "(Branch between nodes BUS1 and BUS4_BUS_BUS2: (1:Line: R=[200 ohm [Base: 100 ohm]] X=[3000 ohm "
            "[Base: 100 ohm]] Gs=[20 S [Base: 10 S]] Bs=[30 S [Base: 10 S]] Closed at first bus=[True] Closed at "
            "second bus=[True] Metal short circuit=[False]))]"
        )
        assert bus.branches[0].first_bus == bus
        assert bus.branches[1].second_bus == bus
        for gen in bus.generators:
            assert gen.bus == bus
        for load in bus.loads:
            assert load.bus == bus
        for bank in bus.capacitor_banks:
            assert bank.bus == bus
        assert repr(bus) == bus_repr

        # Try to add coupled bus to istelf (nothing is done)
        bus.couple_to_bus(bus)
        assert repr(bus) == bus_repr

        # Try to couple bus to a bus already coupled to it
        simple_bus2_copy = deepcopy(simple_bus2)
        simple_bus2_copy.couple_to_bus(cb)
        assert repr(simple_bus2_copy) == repr(simple_bus2)

    def test_coupled_bus_names(self, simple_bus, simple_bus2):
        cb = deepcopy(simple_bus)
        simple_bus2_copy = deepcopy(simple_bus2)

        # Try to couple to a bus representing a generator internal voltage
        cb.couple_to_bus(simple_bus2_copy)
        assert cb.coupled_bus_names == {"BUS", "BUS2"}

    def test_voltage_magnitude(self, simple_bus):
        assert simple_bus.voltage_magnitude == Value(380, Unit.KV, PUBase(10, Unit.KV))

    def test_phase_angle(self, simple_bus):
        assert simple_bus.phase_angle == Value(value=20, unit=Unit.DEG)
