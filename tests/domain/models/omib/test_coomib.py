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

from deeac.domain.models import NetworkState
from deeac.domain.exceptions import GeneratorClusterMemberException


class TestCOOMIB:

    def test_get_generator_angular_deviation(self, case1_coomib):
        generator = next(gen for gen in case1_coomib._non_critical_cluster.generators if gen.name == "GENB1")
        deviation = case1_coomib._get_generator_angular_deviation(
            generator.name,
            case1_coomib._non_critical_cluster,
            0,
            NetworkState.PRE_FAULT
        )
        assert cmath.isclose(deviation, 0.0361554039593541, abs_tol=10e-9)
        deviation2 = case1_coomib._get_generator_angular_deviation(
            generator.name,
            case1_coomib._non_critical_cluster,
            2,
            NetworkState.POST_FAULT
        )
        assert deviation2 == deviation
        with pytest.raises(GeneratorClusterMemberException):
            case1_coomib._get_generator_angular_deviation(
                "FAKE_GEN",
                case1_coomib._non_critical_cluster,
                0,
                NetworkState.PRE_FAULT
            )

    def test_initial_rotor_angle(self, case1_coomib):
        assert cmath.isclose(case1_coomib.initial_rotor_angle, 0.04390471194945145, abs_tol=10e-9)

    def test_properties(self, case1_coomib):
        angle_shift, constant_electric_power, maximum_electric_power = case1_coomib.get_properties(
            NetworkState.PRE_FAULT
        )
        assert cmath.isclose(constant_electric_power, 2.882827255787625, abs_tol=10e-9)
        assert cmath.isclose(maximum_electric_power, 14.898675858973995, abs_tol=10e-9)
        assert cmath.isclose(angle_shift, -0.35977356395458615, abs_tol=10e-9)

    def test_get_electric_power(self, case1_coomib):
        power = case1_coomib.get_electric_power(0.5, NetworkState.DURING_FAULT)
        assert cmath.isclose(power, 4.074210569551228, abs_tol=10e-9)
        power = case1_coomib.get_electric_power(0.5, NetworkState.POST_FAULT)
        assert cmath.isclose(power, 13.232232706730695, abs_tol=10e-9)
