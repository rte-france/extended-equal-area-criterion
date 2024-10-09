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


class TestZOOMIB:

    def test_get_generator_angular_deviation(self, case1_zoomib):
        generator = list(case1_zoomib._critical_cluster.generators)[0]
        assert case1_zoomib._get_generator_angular_deviation(
            generator.name,
            case1_zoomib._critical_cluster,
            0,
            NetworkState.PRE_FAULT
        ) == 0
        assert case1_zoomib._get_generator_angular_deviation(
            generator.name,
            case1_zoomib._critical_cluster,
            3,
            NetworkState.POST_FAULT
        ) == 0
        with pytest.raises(GeneratorClusterMemberException):
            case1_zoomib._get_generator_angular_deviation(
                "FAKE_GEN",
                case1_zoomib._non_critical_cluster,
                0,
                NetworkState.PRE_FAULT
            )

    def test_properties(self, case1_zoomib):
        angle_shift, constant_electric_power, maximum_electric_power = case1_zoomib.get_properties(
            NetworkState.PRE_FAULT
        )
        assert cmath.isclose(constant_electric_power, 2.8828073577774185, abs_tol=10e-9)
        assert cmath.isclose(maximum_electric_power, 14.895545159024438, abs_tol=10e-9)
        assert cmath.isclose(angle_shift, -0.36492296809150343, abs_tol=10e-9)

        assert (angle_shift, constant_electric_power, maximum_electric_power) == case1_zoomib.get_properties(
            NetworkState.PRE_FAULT, 0.4
        )

    def test_initial_rotor_angle(self, case1_zoomib):
        assert cmath.isclose(case1_zoomib.initial_rotor_angle, 0.03884653626803064, abs_tol=10e-9)

    def test_get_electric_power(self, case1_zoomib):
        power = case1_zoomib.get_electric_power(0.5, NetworkState.DURING_FAULT)
        assert cmath.isclose(power, 4.080202873547963, abs_tol=10e-9)
        power = case1_zoomib.get_electric_power(0.5, NetworkState.POST_FAULT)
        assert cmath.isclose(power, 13.258628327836675, abs_tol=10e-9)
