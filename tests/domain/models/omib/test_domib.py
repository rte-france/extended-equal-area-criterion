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


class TestDOMIB:

    def test_get_generator_angular_deviation(self, case1_domib):
        _, transition_time, _ = case1_domib.update_angles[6]
        # GENA1 is alone in its set, its angle is always equal to the PCOA
        assert case1_domib._get_generator_angular_deviation(
            "GENA1",
            case1_domib._critical_cluster,
            0,
            NetworkState.PRE_FAULT
        ) == 0
        # GENB2
        deviation = case1_domib._get_generator_angular_deviation(
            "GENB2",
            case1_domib._non_critical_cluster,
            0,
            NetworkState.PRE_FAULT
        )
        assert cmath.isclose(deviation, 0.02268585659399347, abs_tol=10e-9)
        deviation = case1_domib._get_generator_angular_deviation(
            "GENB2",
            case1_domib._non_critical_cluster,
            transition_time,
            NetworkState.DURING_FAULT
        )
        assert cmath.isclose(deviation, 0.5458956822165073, abs_tol=10e-9)
        # Fake generator
        with pytest.raises(GeneratorClusterMemberException):
            case1_domib._get_generator_angular_deviation(
                "FAKE_GEN",
                case1_domib._non_critical_cluster,
                0,
                NetworkState.PRE_FAULT
            )

    def test_initial_rotor_angle(self, case1_domib):
        assert cmath.isclose(case1_domib.initial_rotor_angle, 0.04390471194945145, abs_tol=10e-9)

    def test_properties(self, case1_domib, case1_coomib):
        # At initial time, should be similar to COOMIB
        angle_shift, constant_electric_power, maximum_electric_power = case1_domib.get_properties(
            NetworkState.DURING_FAULT
        )
        angle_shift_c, constant_electric_power_c, maximum_electric_power_c = case1_coomib.get_properties(
            NetworkState.DURING_FAULT
        )
        assert cmath.isclose(constant_electric_power, constant_electric_power_c, abs_tol=10e-9)
        assert cmath.isclose(maximum_electric_power, maximum_electric_power_c, abs_tol=10e-9)
        assert cmath.isclose(angle_shift, angle_shift_c, abs_tol=10e-9)

        angle_shift, constant_electric_power, maximum_electric_power = case1_domib.get_properties(
            NetworkState.DURING_FAULT,
            0.8695242119762667
        )
        assert cmath.isclose(constant_electric_power, 1.3264297622441759, abs_tol=10e-9)
        assert cmath.isclose(maximum_electric_power, 4.216941691563058, abs_tol=10e-9)
        assert cmath.isclose(angle_shift, -0.1849884012079783, abs_tol=10e-9)
        # Same update angle
        angle_shift2, constant_electric_power2, maximum_electric_power2 = case1_domib.get_properties(
            NetworkState.DURING_FAULT,
            0.87
        )
        assert cmath.isclose(constant_electric_power, constant_electric_power2, abs_tol=10e-9)
        assert cmath.isclose(maximum_electric_power, maximum_electric_power2, abs_tol=10e-9)
        assert cmath.isclose(angle_shift, angle_shift2, abs_tol=10e-9)

        # Post fault
        angle_shift, constant_electric_power, maximum_electric_power = case1_domib.get_properties(
            NetworkState.POST_FAULT,
            14.5
        )
        assert cmath.isclose(constant_electric_power, 3.731497272571173, abs_tol=10e-9)
        assert cmath.isclose(maximum_electric_power, 11.585276171616112, abs_tol=10e-9)
        assert cmath.isclose(angle_shift, -0.2703753577434177, abs_tol=10e-9)
        # First update point
        angle_shift, constant_electric_power, maximum_electric_power = case1_domib.get_properties(
            NetworkState.POST_FAULT,
            1.87
        )
        assert cmath.isclose(constant_electric_power, 3.724377287690065, abs_tol=10e-9)
        assert cmath.isclose(maximum_electric_power, 11.853719953300255, abs_tol=10e-9)
        assert cmath.isclose(angle_shift, -0.2895261656388814, abs_tol=10e-9)

    def test_get_electric_power(self, case1_domib):
        power = case1_domib.get_electric_power(0.5, NetworkState.DURING_FAULT, True)
        assert cmath.isclose(power, 4.074210569551228, abs_tol=10e-9)
        power = case1_domib.get_electric_power(0.5, NetworkState.POST_FAULT, True)
        assert cmath.isclose(power, 13.232232706730697, abs_tol=10e-9)

        power = case1_domib.get_electric_power(0.5, NetworkState.DURING_FAULT, False)
        assert cmath.isclose(power, 4.031068356706558, abs_tol=10e-9)
        power = case1_domib.get_electric_power(0.5, NetworkState.POST_FAULT, False)
        assert cmath.isclose(power, 12.601645579562355, abs_tol=10e-9)
