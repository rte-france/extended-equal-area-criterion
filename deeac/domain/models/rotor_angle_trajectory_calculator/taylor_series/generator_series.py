# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import numpy as np

from collections import defaultdict
from typing import Set, Tuple

from deeac.domain.models import DynamicGenerator, Network, NetworkState
from deeac.domain.models.rotor_angle_trajectory_calculator import (
    GeneratorRotorAnglesTrajectoryCalculator, GeneratorTrajectoryTime
)
from deeac.domain.exceptions import GeneratorInertiaException


class GeneratorTaylorSeries(GeneratorRotorAnglesTrajectoryCalculator):
    """
    Class modeling an Individual Taylor Series used to derive the rotor angle of a single generator at a specific time.
    """

    def __init__(self, network: Network, transition_time_shift: float = 0):
        """
        Initialize the series with the network containing the generators.

        :param network: Network to use with this series.
        :param transition_time_shift: Shift (s) to apply to the transition time. It is only unsed to compute the
                                      rotor angles after the transition time, allowing to obtain improved curves in
                                      further analyses. The angle outputted for the transition time is not altered by
                                      this shift.
        """
        super().__init__(network, transition_time_shift)

        # Initialize containers for intermediate results to improve performances
        self._angular_speed_derivatives = defaultdict(lambda: defaultdict(dict))

    def _get_power_matrices(
        self, generators: Set[DynamicGenerator], network_state: NetworkState, time: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes the power matrices for the Taylor series angle computation
        :return: matrices pair as coefficient of the second and fourth order angle derivative respectively
        """
        n = len(generators)
        matrix_a = np.zeros((n, n))
        matrix_b = np.zeros((n, n))

        voltages = np.array([abs(g.generator.internal_voltage) for g in generators])
        angles = np.array([g.get_rotor_angle(time) for g in generators])
        names = [g.bus.name for g in generators]

        for i in range(n):
            voltage_i = voltages[i]
            angle_i = angles[i]
            name_i = names[i]

            for j in range(i, n):
                voltage_j = voltages[j]
                angle_j = angles[j]
                name_j = names[j]

                admittance_module, admittance_phase = self._network.get_admittance(name_i, name_j, network_state)
                angle = angle_i - angle_j - admittance_phase
                cos_angle = np.cos(angle).real
                sin_angle = np.sin(angle).real
                matrix_a[i, j] = voltage_i * voltage_j * admittance_module * cos_angle
                matrix_b[i, j] = voltage_i * voltage_j * admittance_module * sin_angle

                if i != j:
                    matrix_a[j, i] = matrix_a[i, j]
                    matrix_b[j, i] = matrix_b[i, j]

        return matrix_a, matrix_b

    def _add_trajectory_point(
        self, generators: Set[DynamicGenerator], from_trajectory_time: GeneratorTrajectoryTime,
        to_trajectory_time: GeneratorTrajectoryTime
    ):
        """
        Add a new trajectory point at a specific time to a set of generators.
        Adding a point consists in computing the value of the generator rotor angle at a specific time moving it from a
        previous point along its trajectory.
        A new rotor angle value is added to each dynamic generator at the specified time.

        :param generators: Dynamic generators whose angle must be computed. They must contain their rotor angle value
                           at time t = from_time.
        :param from_trajectory_time: Time associated to the values of the generator angles at the previous point.
        :param to_trajectory_time: Target time corresponding to the new values of the generator angles to be computed.
        :raise GeneratorInertiaException if a generator has no inertia.
        """
        if any(generator.inertia_coefficient == 0 for generator in generators):
            raise GeneratorInertiaException(
                [g.name for g in generators if g.inertia_coefficient == 0][0]
            )

        from_time = from_trajectory_time.time
        to_time = to_trajectory_time.time
        network_state = from_trajectory_time.network_state
        pulse = self._network.pulse

        generators = list(generators)
        matrix_a, matrix_b = self._get_power_matrices(generators, network_state, from_time)

        inertia = np.array([g.inertia_coefficient for g in generators])
        mech_power = np.array([g.mechanical_power for g in generators])
        rotor_angles = np.array([g.get_rotor_angle(from_time) for g in generators])
        angular_speeds = np.array([g.get_angular_speed(from_time) * pulse for g in generators])

        sum_matrix_a = matrix_a.sum(axis=1)
        derivatives_second = (mech_power - sum_matrix_a) * pulse / inertia

        delta_speed = angular_speeds[:, None] - angular_speeds
        derivatives_third = (np.sum(matrix_b * delta_speed, axis=1)) * pulse / inertia

        delta_second = derivatives_second[:, None] - derivatives_second
        delta_first_squared = delta_speed ** 2
        fourth_sum = matrix_a * delta_first_squared + matrix_b * delta_second
        derivatives_fourth = (np.sum(fourth_sum, axis=1)) * pulse / inertia

        delta_third = derivatives_third[:, None] - derivatives_third
        delta_first_cubed = delta_speed ** 3
        fifth_sum = 3 * matrix_a * delta_speed * delta_second + matrix_b * (delta_third - delta_first_cubed)
        derivatives_fifth = (np.sum(fifth_sum, axis=1)) * pulse / inertia

        dt = to_time - from_time
        dt2, dt3, dt4 = dt ** 2, dt ** 3, dt ** 4

        delta_angles = (
            dt * angular_speeds +
            dt2 * derivatives_second / 2 +
            dt3 * derivatives_third / 6 +
            dt4 * derivatives_fourth / 24
        )
        new_angles = rotor_angles + delta_angles

        delta_speeds = (
            dt * derivatives_second +
            dt2 * derivatives_third / 2 +
            dt3 * derivatives_fourth / 6 +
            dt4 * derivatives_fifth / 24
        )
        new_speeds = angular_speeds + delta_speeds
        new_speeds /= pulse

        for i, generator in enumerate(generators):
            generator.add_rotor_angle(to_time, new_angles[i])
            generator.add_angular_speed(to_time, new_speeds[i])
            generator.add_network_state(to_time, to_trajectory_time.network_state)

