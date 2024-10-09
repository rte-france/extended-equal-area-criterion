# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from copy import deepcopy

from .dto_comparators import dtos_are_equal
from deeac.domain.ports.dtos import Value, Unit
from deeac.domain.ports.dtos.topology import SlackBus, Generator


class TestDtoComparators:

    def test_dtos_are_equal(self):
        # Integers
        assert dtos_are_equal(1, 1)
        assert not dtos_are_equal(1, 2)
        # Floats
        assert not 0.1 + 0.2 == 0.3
        assert dtos_are_equal(0.1 + 0.2, 0.3)
        assert not dtos_are_equal(0.1 + 0.3, 0.5)
        # Strings
        assert dtos_are_equal("DTO1", "DTO1")
        assert not dtos_are_equal("DTO1", "DTO2")
        # Base models
        slack_bus1 = SlackBus(
            name="NHVCEQ",
            base_voltage=Value(value=100, unit=Unit.KV),
            phase_angle=Value(value=0, unit=Unit.DEG)
        )
        gen1 = Generator(
            name="GEN A1",
            connected=True,
            bus=slack_bus1,
            min_active_power=Value(value=-999999, unit=Unit.MW),
            active_power=Value(value=900, unit=Unit.MW),
            max_active_power=Value(value=999999, unit=Unit.MW),
            min_reactive_power=Value(value=-9999, unit=Unit.MVAR),
            reactive_power=Value(value=0, unit=Unit.MVAR),
            max_reactive_power=Value(value=9999, unit=Unit.MVAR),
            target_voltage=Value(value=24, unit=Unit.KV),
            direct_transient_reactance=Value(value=0.420*24**2/100, unit=Unit.OHM),
            inertia_constant=Value(value=6.3, unit=Unit.MWS_PER_MVA),
            regulating=True
        )
        gen2 = deepcopy(gen1)

        assert(dtos_are_equal(gen1, gen2))
        gen2.connected = False
        assert(not dtos_are_equal(gen1, gen2))
        gen2.connected = True
        assert(dtos_are_equal(gen1, gen2))

        ap = gen2.active_power
        gen2.active_power = Value(value=300, unit=Unit.MW)
        assert(not dtos_are_equal(gen1, gen2))
        gen2.active_power = ap
        assert(dtos_are_equal(gen1, gen2))

        gen2.bus.name = "TEST"
        assert(not dtos_are_equal(gen1, gen2))
        gen2.bus.name = "NHVCEQ"
        assert(dtos_are_equal(gen1, gen2))

        # Lists
        assert dtos_are_equal([1, 2, "DTO", gen1], [1, 2, "DTO", gen2])
        assert not dtos_are_equal([1, 1, "DTO"], [1, 2, "DTO"])
        assert not dtos_are_equal([1, 2, "DTO1"], [1, 2, "DTO"])
        gen2.bus.name = "TEST"
        assert not dtos_are_equal([1, 2, "DTO", gen1], [1, 2, "DTO", gen2])
        gen2.bus.name = "NHVCEQ"

        # Dictionaries
        assert dtos_are_equal({1: 1, 2: 2, 3: "DTO", 4: gen1}, {1: 1, 2: 2, 3: "DTO", 4: gen2})
        assert not dtos_are_equal({1: 1, 2: 2, 3: "DTO", 4: gen1}, {1: 1, 2: 9, 3: "DTO", 4: gen2})
        assert not dtos_are_equal({1: 1, 2: 2, 3: "DTO", 4: gen1}, {1: 1, 9: 2, 3: "DTO", 4: gen2})
        gen2.bus.name = "TEST"
        assert not dtos_are_equal({1: 1, 2: 2, 3: "DTO", 4: gen1}, {1: 1, 2: 2, 3: "DTO", 4: gen2})
        gen2.bus.name = "NHVCEQ"
