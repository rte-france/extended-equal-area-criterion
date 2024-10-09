# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import cmath
import numpy as np

from deeac.domain.models import Value, Unit, PUBase, Bus


class TestCapacitorBank:

    def test_repr(self, simple_capacitor_bank):
        assert repr(simple_capacitor_bank) == (
            "Capacitor bank: Name=[BANK] Bus=[BUS] P=[0 MW [Base: 10 MW]] Q=[150 MVAr [Base: 10 MVAr]]"
        )

    def test_complex_power(self, simple_capacitor_bank):
        assert cmath.isclose(simple_capacitor_bank.complex_power, 15j, abs_tol=10e-9)

    def test_admittance(self, simple_capacitor_bank):
        assert cmath.isclose(simple_capacitor_bank.admittance, -10.416666666666666j, abs_tol=10e-9)

    def test_bus(self, simple_capacitor_bank):
        assert isinstance(simple_capacitor_bank.bus, Bus)
        assert simple_capacitor_bank.bus.name == "BUS"
        new_bus = Bus(
            "NEWBUS",
            Value(100, Unit.KV),
            Value(10, Unit.KV, PUBase(10, unit=Unit.KV)),
            Value(5, Unit.DEG)
        )
        simple_capacitor_bank.bus = new_bus
        assert simple_capacitor_bank.bus.name == "NEWBUS"
        assert cmath.isclose(simple_capacitor_bank.admittance, -15j, abs_tol=10e-9)
        new_bus = Bus(
            "NEWBUS2",
            Value(100, Unit.KV),
            Value(0, Unit.KV, PUBase(10, unit=Unit.KV)),
            Value(0, Unit.DEG)
        )
        simple_capacitor_bank.bus = new_bus
        assert simple_capacitor_bank.admittance == complex(np.inf, np.NINF)
