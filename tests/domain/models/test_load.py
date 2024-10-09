# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import cmath

from deeac.domain.models import Value, Unit, PUBase, Bus


class TestLoad:

    def test_repr(self, simple_load):
        assert repr(simple_load) == (
            "Load: Name=[LOAD] Bus=[BUS] P=[100 MW [Base: 10 MW]] Q=[30000 kVAr [Base: 10 MVAr]] "
            "Connected=[True]"
        )

    def test_complex_power(self, simple_load):
        assert cmath.isclose(simple_load.complex_power, 10 + 3j, abs_tol=10e-9)
        # Check if disconnected
        simple_load.connected = False
        assert simple_load.complex_power == 0j
        simple_load.connected = True

    def test_admittance(self, simple_load):
        assert cmath.isclose(simple_load.admittance, 6.944444444444445 - 2.083333333333333j, abs_tol=10e-9)
        # Check if disconnected
        simple_load.connected = False
        assert simple_load.admittance == 0j
        simple_load.connected = True

    def test_bus(self, simple_load):
        assert isinstance(simple_load.bus, Bus)
        assert simple_load.bus.name == "BUS"
        new_bus = Bus(
            "NEWBUS",
            Value(100, Unit.KV),
            Value(10, Unit.KV, PUBase(10, unit=Unit.KV)),
            Value(5, Unit.DEG)
        )
        simple_load.bus = new_bus
        assert simple_load.bus.name == "NEWBUS"
        assert cmath.isclose(simple_load.admittance, 10 - 3j, abs_tol=10e-9)
        new_bus = Bus(
            "NEWBUS2",
            Value(100, Unit.KV),
            Value(0, Unit.KV, PUBase(10, unit=Unit.KV)),
            Value(0, Unit.DEG)
        )
        simple_load.bus = new_bus
        assert simple_load.admittance == 0


class TestFictiveLoad:

    def test_repr(self, simple_fictive_load):
        assert repr(simple_fictive_load) == (
            "Fictive load: Name=[FICTIVE_LOAD] Bus=[BUS] Y=[(3+2j) S] Connected=[True]"
        )

    def test_complex_power(self, simple_fictive_load):
        assert simple_fictive_load.complex_power == 0j

    def test_admittance(self, simple_fictive_load):
        admittance = 3 + 2j
        assert simple_fictive_load.admittance == admittance
        # Check if disconnected
        simple_fictive_load.connected = False
        assert simple_fictive_load.admittance == 0j
        simple_fictive_load.connected = True
        new_bus = Bus(
            "NEWBUS2",
            Value(100, Unit.KV),
            Value(0, Unit.KV, PUBase(10, unit=Unit.KV)),
            Value(0, Unit.DEG)
        )
        simple_fictive_load.bus = new_bus
        # Admittance is constant
        assert simple_fictive_load.admittance == admittance
