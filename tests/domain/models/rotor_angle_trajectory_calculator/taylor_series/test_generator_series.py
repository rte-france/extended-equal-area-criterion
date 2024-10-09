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
from deeac.domain.models.rotor_angle_trajectory_calculator.taylor_series import GeneratorTaylorSeries
from deeac.domain.models.rotor_angle_trajectory_calculator.generator_calculator import GeneratorTrajectoryTime
from deeac.domain.exceptions import UnknownRotorAngleException


class TestGeneratorTaylorSeries:

    def test_get_power_matrices(self, case1_network_line_fault, case1_zoomib):
        generators = case1_zoomib.critical_cluster.generators.union(case1_zoomib.non_critical_cluster.generators)
        series = GeneratorTaylorSeries(case1_network_line_fault)
        matrix_a, matrix_b = series._get_power_matrices(generators, NetworkState.POST_FAULT, 0)

        assert cmath.isclose(sum(sum(row) for row in matrix_a), 36.82365611992029, abs_tol=10e-9)
        assert cmath.isclose(sum(sum(row) for row in matrix_b), 16.290559366416332, abs_tol=10e-9)

    def test_add_trajectory_point(
        self, case1_network_line_fault, case1_line_fault_zoomib_eac, case1_line_fault_omib_taylor_series
    ):
        case1_zoomib = case1_line_fault_zoomib_eac.omib
        generators = case1_zoomib.critical_cluster.generators.union(case1_zoomib.non_critical_cluster.generators)
        series = GeneratorTaylorSeries(case1_network_line_fault)

        # Compute angles at critical clearing time / 2
        critical_angle = case1_line_fault_zoomib_eac.critical_clearing_angle
        cc_time = case1_line_fault_omib_taylor_series.get_trajectory_times([critical_angle], critical_angle)[0]
        target_time = cc_time / 2

        from_traj_time = GeneratorTrajectoryTime(time=0, network_state=NetworkState.DURING_FAULT)
        to_traj_time = GeneratorTrajectoryTime(time=target_time, network_state=NetworkState.DURING_FAULT)

        for generator in generators:
            with pytest.raises(UnknownRotorAngleException):
                generator.get_rotor_angle(target_time)
        series._add_trajectory_point(generators, from_traj_time, to_traj_time)

        generator = next(generator for generator in generators if generator.name == "GENA1")
        angle = generator.get_rotor_angle(target_time)
        assert cmath.isclose(angle, 0.3965789628549688, abs_tol=10e-9)

        generator = next(generator for generator in generators if generator.name == "GENB1")
        angle = generator.get_rotor_angle(target_time)
        assert cmath.isclose(angle, 0.36271940510891865, abs_tol=10e-9)

    def test_update_generator_angles_at_times(self, case1_domib, case1_line_fault_dynamic_generators_updated):
        # Update already performed in the conftest file
        times = list(case1_line_fault_dynamic_generators_updated)[0].observation_times

        gen_a1 = next(gen for gen in case1_domib._generators if gen.name == "GENA1")
        gen_b2 = next(gen for gen in case1_domib._generators if gen.name == "GENB2")
        gen_a1_angles = [
            0.02241828183301042, 0.08415361520064944, 0.2651482973812792, 0.553383898406644, 0.931364757232415,
            1.3810652896081055, 1.767587143986939, 2.0665869048004026, 2.2978924605731983, 2.4837927756470983,
            2.6452847028867224
        ]
        gen_b2_angles = [
            0.19089541219657244, 0.21412836451318545, 0.2831676420930025, 0.3960845011441308, 0.54982348236491,
            0.7404623780079412, 0.9165527348823206, 1.0665520019768582, 1.1871001037191546, 1.2764265815297453,
            1.3340385221910687
        ]
        for i, time in enumerate(times):
            assert cmath.isclose(gen_a1.get_rotor_angle(time), gen_a1_angles[i], abs_tol=10e-9)
            assert cmath.isclose(gen_b2.get_rotor_angle(time), gen_b2_angles[i], abs_tol=10e-9)
