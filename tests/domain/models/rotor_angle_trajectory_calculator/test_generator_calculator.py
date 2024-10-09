# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import cmath

from deeac.domain.models import NetworkState, DynamicGenerator
from deeac.domain.models.rotor_angle_trajectory_calculator.taylor_series import GeneratorTaylorSeries
from deeac.domain.models.rotor_angle_trajectory_calculator import GeneratorTrajectoryTime


class TestGeneratorCalculator:

    def test_compute_generator_electric_power(
        self, case1_network_line_fault, case1_line_fault_omib_taylor_series, case1_line_fault_zoomib_eac
    ):
        generators = case1_line_fault_omib_taylor_series._omib.critical_cluster.generators.union(
            case1_line_fault_omib_taylor_series._omib.non_critical_cluster.generators
        )
        series = GeneratorTaylorSeries(case1_network_line_fault)

        generator = next(gen for gen in generators if gen.name == "GENA1")
        time = GeneratorTrajectoryTime(time=0, network_state=NetworkState.DURING_FAULT)
        series._compute_generator_electric_power(generator, generators, time, True)
        electric_power = series._generator_electric_powers["GENA1"][time.network_state][time.time]
        assert cmath.isclose(electric_power, 1.6845081464890275, abs_tol=10e-9)
        electric_power_derivative = (
            series._neg_generator_electric_power_derivatives["GENA1"][time.network_state][time.time]
        )
        assert cmath.isclose(electric_power_derivative, 19.78924476196252, abs_tol=10e-9)

        time = GeneratorTrajectoryTime(time=0, network_state=NetworkState.PRE_FAULT)
        series._compute_generator_electric_power(generator, generators, time)
        assert time.network_state not in series._neg_generator_electric_power_derivatives["GENA1"]

        critical_clearing_angle = case1_line_fault_zoomib_eac.critical_clearing_angle
        critical_clearing_time = case1_line_fault_omib_taylor_series.get_trajectory_times(
            [critical_clearing_angle],
            critical_clearing_angle
        )[0]
        from_time = GeneratorTrajectoryTime(time=0, network_state=NetworkState.DURING_FAULT)
        to_time = GeneratorTrajectoryTime(time=critical_clearing_time, network_state=NetworkState.POST_FAULT)
        series._add_trajectory_point(
            generators=generators,
            from_trajectory_time=from_time,
            to_trajectory_time=to_time
        )
        series._compute_generator_electric_power(generator, generators, to_time)
        electric_power = series._generator_electric_powers["GENA1"][to_time.network_state][to_time.time]
        assert cmath.isclose(electric_power, 16.00835738499264, abs_tol=10e-9)

    def test_get_update_time_sequence(self, case1_network_line_fault):
        series = GeneratorTaylorSeries(case1_network_line_fault)
        # 2 during-fault intervals and 5 post-fault ones
        sequence = series._get_update_time_sequence(10, 20, 2, 5)
        expected_sequence = [
            (0, NetworkState.DURING_FAULT),
            (5, NetworkState.DURING_FAULT),
            (10, NetworkState.POST_FAULT),
            (12, NetworkState.POST_FAULT),
            (14, NetworkState.POST_FAULT),
            (16, NetworkState.POST_FAULT),
            (18, NetworkState.POST_FAULT),
            (20, NetworkState.POST_FAULT)
        ]
        for id, element in enumerate(sequence):
            assert element.time == expected_sequence[id][0]
            assert element.network_state == expected_sequence[id][1]

        # Tries adding a time shift
        series = GeneratorTaylorSeries(case1_network_line_fault, transition_time_shift=1)
        # 2 during-fault intervals and 5 post-fault ones
        sequence = series._get_update_time_sequence(10, 20, 2, 5)
        expected_sequence = [
            (0, NetworkState.DURING_FAULT),
            (5, NetworkState.DURING_FAULT),
            (10, NetworkState.DURING_FAULT),
            (11, NetworkState.POST_FAULT),
            (12, NetworkState.POST_FAULT),
            (14, NetworkState.POST_FAULT),
            (16, NetworkState.POST_FAULT),
            (18, NetworkState.POST_FAULT),
            (20, NetworkState.POST_FAULT)
        ]
        for id, element in enumerate(sequence):
            assert element.time == expected_sequence[id][0]
            assert element.network_state == expected_sequence[id][1]

    def test_update_generator_angles(
        self, case1_network_line_fault, case1_line_fault_zoomib_eac, case1_line_fault_omib_taylor_series
    ):
        # Results with DEEAC and ZOOMIB
        critical_angle = case1_line_fault_zoomib_eac.critical_clearing_angle
        maximum_angle = case1_line_fault_zoomib_eac.maximum_angle
        angles = [critical_angle, maximum_angle]
        critical_time, maximum_time = case1_line_fault_omib_taylor_series.get_trajectory_times(angles, critical_angle)

        # No time shift
        generators = {
            DynamicGenerator(gen) for gen in case1_network_line_fault.get_state(NetworkState.POST_FAULT).generators
        }
        series = GeneratorTaylorSeries(case1_network_line_fault)
        series.update_generator_angles(generators, critical_time, maximum_time, 5, 5)
        first_times = list(generators)[0].observation_times
        gen_a1 = next(gen for gen in generators if gen.name == "GENA1")
        gen_b2 = next(gen for gen in generators if gen.name == "GENB2")
        gen_a1_angles = [
            0.02241828183301042, 0.08415361520064944, 0.2651482973812792, 0.553383898406644, 0.931364757232415,
            1.3810652896081055, 1.767587143986939, 2.0665869048004026, 2.2978924605731983, 2.4837927756470983,
            2.6452847028867224
        ]
        gen_b2_angles = [
            0.19089541219657244, 0.21412836451318545, 0.2831676420930025, 0.3960845011441308,0.54982348236491,
            0.7404623780079412, 0.9165527348823206, 1.0665520019768582, 1.1871001037191549, 1.2764265815297455,
            1.334038522191069
        ]
        for i, time in enumerate(first_times):
            assert cmath.isclose(gen_a1.get_rotor_angle(time), gen_a1_angles[i], abs_tol=10e-9)
            assert cmath.isclose(gen_b2.get_rotor_angle(time), gen_b2_angles[i], abs_tol=10e-9)

        # With time shift
        generators = {
            DynamicGenerator(gen) for gen in case1_network_line_fault.get_state(NetworkState.POST_FAULT).generators
        }
        series = GeneratorTaylorSeries(case1_network_line_fault, transition_time_shift=0.02)
        series.update_generator_angles(generators, critical_time, maximum_time, 5, 5)
        second_times = list(generators)[0].observation_times
        gen_a1 = next(gen for gen in generators if gen.name == "GENA1")
        gen_b2 = next(gen for gen in generators if gen.name == "GENB2")
        gen_a1_angles = [
            0.02241828183301042, 0.08415361520064944, 0.2651482973812792, 0.553383898406644, 0.931364757232415,
            1.3810652896081055, 1.8151058264865383, 2.1772273312180213, 2.482644162705571, 2.765807944620238,
            3.06466765116879
        ]
        gen_b2_angles = [
            0.19089541219657244, 0.21412836451318545, 0.2831676420930025, 0.3960845011441308, 0.54982348236491,
            0.7404623780079412, 0.9323220813164971, 1.1020666723546306, 1.242293795444543, 1.3517039504397261,
            1.4305201610782377
        ]
        for i, time in enumerate(second_times):
            assert cmath.isclose(gen_a1.get_rotor_angle(time), gen_a1_angles[i], abs_tol=10e-9)
            assert cmath.isclose(gen_b2.get_rotor_angle(time), gen_b2_angles[i], abs_tol=10e-9)

        # Check that critical time is still there with the right state
        assert gen_a1.get_network_state(critical_time) == NetworkState.POST_FAULT
        assert gen_b2.get_network_state(critical_time) == NetworkState.POST_FAULT
        assert len(second_times) == len(first_times)
        for i, time in enumerate(second_times):
            assert cmath.isclose(time, first_times[i], abs_tol=10e-9)
