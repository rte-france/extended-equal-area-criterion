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

from deeac.domain.models import BusType, Bus, Unit, Value, PUBase, Generator, GeneratorType, NetworkState
from deeac.domain.exceptions import (
    DisconnectedElementException, ZeroDirectTransientReactanceException, UnknownRotorAngleException,
    UnknownAngularSpeedException, UnknownNetworkStateException
)


class TestGenerator:

    def test_repr(self, simple_generator):
        assert repr(simple_generator) == (
            "Generator: Name=[GEN] Type=[PV] Bus=[BUS] "
            "x'd=[100 ohm [Base: 10 ohm]] H=[5 MWs/MVA] Pmin=[0 MW [Base: 100 MW]] P=[900 MW [Base: 100 MW]] "
            "Pmax=[1000 MW [Base: 100 MW]] Qmin=[100 MW [Base: 100 MW]] Q=[300 MVAr [Base: 100 MVAr]] Qmax=[700 MW "
            "[Base: 100 MW]] |Vt|=[380 kV [Base: 10 kV]] Connected=[True]"
        )

    def test_max_active_power(self, simple_generator):
        assert simple_generator.max_active_power == 10
    
    def test_active_power(self, simple_generator):
        assert simple_generator.active_power == 9

    def test_direct_transient_reactance(self, simple_generator):
        assert simple_generator.direct_transient_reactance == 10
        # Check if disconnected
        simple_generator.connected = False
        with pytest.raises(DisconnectedElementException):
            simple_generator.direct_transient_reactance
        simple_generator.connected = True
        with pytest.raises(ZeroDirectTransientReactanceException):
            Generator(
                "GEN",
                GeneratorType.PQ,
                simple_generator.bus,
                Value(0, Unit.KV, PUBase(10, Unit.KV)),
                Value(10, Unit.MWS_PER_MVA),
                Value(0, Unit.MW),
                Value(10, Unit.MW, PUBase(10, Unit.MW)),
                Value(10, Unit.MW, PUBase(10, Unit.MW)),
                Value(10, Unit.MVAR, PUBase(10, Unit.MVAR)),
                Value(20, Unit.MVAR, PUBase(10, Unit.MVAR)),
                Value(30, Unit.MVAR, PUBase(10, Unit.MVAR)),
                None
            )

    def test_direct_transient_admittance(self, simple_generator):
        assert cmath.isclose(simple_generator.direct_transient_admittance, 1 / 10j, abs_tol=10e-9)
        # Check if disconnected
        simple_generator.connected = False
        assert simple_generator.direct_transient_admittance == 0j
        simple_generator.connected = True

    def test_complex_power(self, simple_generator):
        assert cmath.isclose(simple_generator.complex_power, 9 + 3j, abs_tol=10e-9)
        # Check if disconnected
        simple_generator.connected = False
        assert simple_generator.complex_power == 0j
        simple_generator.connected = True

    def test_internal_voltage(self, simple_generator):
        assert cmath.isclose(simple_generator.internal_voltage, 26.2 + 75j, abs_tol=10e-9)
        # Check if disconnected
        simple_generator.connected = False
        assert simple_generator.internal_voltage == 0j
        simple_generator.connected = True
        # Check if connected to fictive internal voltage bus
        simple_generator.bus._type = BusType.GEN_INT_VOLT
        # Force update of internal voltage as bus changed
        simple_generator.compute_internal_voltage()
        assert cmath.isclose(simple_generator.internal_voltage, simple_generator.bus.voltage, abs_tol=10e-9)

    def test_rotor_angle(self, simple_generator):
        assert cmath.isclose(simple_generator.rotor_angle, 1.2347155432180623, abs_tol=10e-9)
        # Check if disconnected
        simple_generator.connected = False
        assert simple_generator.rotor_angle == 0
        simple_generator.connected = True

    def test_mechanical_power(self, simple_generator):
        assert cmath.isclose(simple_generator.mechanical_power, 9.0, abs_tol=10e-9)
        # Check if disconnected
        simple_generator.connected = False
        assert simple_generator.mechanical_power == 0
        simple_generator.connected = True

    def test_inertia_coefficient(self, simple_generator):
        assert simple_generator.inertia_coefficient == 10

    def test_bus(self, simple_generator):
        assert isinstance(simple_generator.bus, Bus)
        assert simple_generator.bus.name == "BUS"
        new_bus = Bus(
            "NEWBUS",
            Value(100, Unit.KV),
            Value(10, Unit.KV, PUBase(10, unit=Unit.KV)),
            Value(5, Unit.DEG)
        )
        simple_generator.bus = new_bus
        assert simple_generator.bus.name == "NEWBUS"
        assert cmath.isclose(simple_generator.internal_voltage, 23.038018793554876 + 92.35935085343449j, abs_tol=10e-9)
        new_bus = Bus(
            "NEWBUS",
            Value(100, Unit.KV),
            Value(0, Unit.KV, PUBase(10, unit=Unit.KV)),
            Value(0, Unit.DEG)
        )
        simple_generator.bus = new_bus
        assert simple_generator.internal_voltage == 0j


class TestDynamicGenerator:

    def test_repr(self, simple_dynamic_generator, simple_generator):
        assert repr(simple_dynamic_generator) == (
            f"Dynamic generator: Name=[GEN] Bus=[BUS] Connected=[True] "
            f"Rotor Angles=[(t=0s, δ={simple_generator.rotor_angle}rad), "
            f"(t=1s, δ=4.5rad), (t=2s, δ=8.1rad)] "
            f"Angular Speeds=[(t=0s, ω=0p.u.), (t=1s, ω=-3.4p.u.), (t=2s, ω=4.1p.u.)]"
        )

    def test_generator(self, simple_dynamic_generator, simple_generator):
        assert simple_dynamic_generator.generator == simple_generator

    def test_name(self, simple_dynamic_generator, simple_generator):
        assert simple_dynamic_generator.name == simple_generator.name

    def test_bus(self, simple_dynamic_generator, simple_generator):
        assert simple_dynamic_generator.bus == simple_generator.bus

    def test_active_power(self, simple_dynamic_generator, simple_generator):
        assert simple_dynamic_generator.active_power == simple_generator.active_power

    def test_mechanical_power(self, simple_dynamic_generator, simple_generator):
        assert simple_dynamic_generator.mechanical_power == simple_generator.mechanical_power

    def test_observation_times(self, simple_dynamic_generator):
        assert simple_dynamic_generator.observation_times == [0, 1, 2]

    def test_inertia_coefficient(self, simple_dynamic_generator, simple_generator):
        assert simple_dynamic_generator.inertia_coefficient == simple_generator.inertia_coefficient

    def test_get_rotor_angle(self, simple_dynamic_generator, simple_generator):
        assert simple_dynamic_generator.get_rotor_angle(0) == simple_generator.rotor_angle
        assert simple_dynamic_generator.get_rotor_angle(1) == 4.5
        assert simple_dynamic_generator.get_rotor_angle(2) == 8.1
        with pytest.raises(UnknownRotorAngleException):
            simple_dynamic_generator.get_rotor_angle(3)

    def test_add_rotor_angle(self, simple_dynamic_generator):
        with pytest.raises(UnknownRotorAngleException):
            simple_dynamic_generator.get_rotor_angle(3)
        simple_dynamic_generator.add_rotor_angle(3, 10)
        simple_dynamic_generator.get_rotor_angle(3) == 10

    def test_get_angular_speed(self, simple_dynamic_generator):
        assert simple_dynamic_generator.get_angular_speed(0) == 0
        assert simple_dynamic_generator.get_angular_speed(1) == -3.4
        assert simple_dynamic_generator.get_angular_speed(2) == 4.1
        with pytest.raises(UnknownAngularSpeedException):
            simple_dynamic_generator.get_angular_speed(3)

    def test_add_angular_speed(self, simple_dynamic_generator):
        with pytest.raises(UnknownAngularSpeedException):
            simple_dynamic_generator.get_angular_speed(3)
        simple_dynamic_generator.add_angular_speed(3, 10)
        simple_dynamic_generator.get_angular_speed(3) == 10

    def test_get_network_state(self, simple_dynamic_generator):
        assert simple_dynamic_generator.get_network_state(0) == NetworkState.PRE_FAULT
        assert simple_dynamic_generator.get_network_state(1) == NetworkState.DURING_FAULT
        assert simple_dynamic_generator.get_network_state(2) == NetworkState.POST_FAULT
        with pytest.raises(UnknownNetworkStateException):
            simple_dynamic_generator.get_network_state(3)
    
    def test_add_network_state(self, simple_dynamic_generator):
        with pytest.raises(UnknownNetworkStateException):
            simple_dynamic_generator.get_network_state(3)
        simple_dynamic_generator.add_network_state(3, NetworkState.POST_FAULT)
        simple_dynamic_generator.get_network_state(3) == NetworkState.POST_FAULT

    def test_delete(self, simple_dynamic_generator):
        assert simple_dynamic_generator.get_rotor_angle(1) == 4.5
        assert simple_dynamic_generator.get_angular_speed(1) == -3.4
        assert simple_dynamic_generator.get_network_state(1) == NetworkState.DURING_FAULT
        simple_dynamic_generator.delete(1)
        with pytest.raises(UnknownRotorAngleException):
            assert simple_dynamic_generator.get_rotor_angle(1)
        with pytest.raises(UnknownAngularSpeedException):
            simple_dynamic_generator.get_angular_speed(1)
        with pytest.raises(UnknownNetworkStateException):
            simple_dynamic_generator.get_network_state(1)

        # Check that other points were not deleted
        assert simple_dynamic_generator.get_rotor_angle(2) == 8.1

    def test_reset(self, simple_dynamic_generator):
        assert simple_dynamic_generator.get_rotor_angle(2) == 8.1
        simple_dynamic_generator.reset()
        with pytest.raises(UnknownRotorAngleException):
            simple_dynamic_generator.get_rotor_angle(2)
        assert simple_dynamic_generator.get_angular_speed(0) == 0
