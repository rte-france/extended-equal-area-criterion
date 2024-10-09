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

        matrix_a = np.zeros((len(generators), len(generators)))
        matrix_b = np.zeros((len(generators), len(generators)))

        for i, generator_i in enumerate(generators):
            voltage_i = abs(generator_i.generator.internal_voltage)
            angle_i = generator_i.get_rotor_angle(time)
            name_i = generator_i.bus.name

            for j, generator_j in enumerate(generators):
                voltage_j = abs(generator_j.generator.internal_voltage)
                angle_j = generator_j.get_rotor_angle(time)
                name_j = generator_j.bus.name

                admittance_module, admittance_phase = self._network.get_admittance(name_i, name_j, network_state)

                angle = angle_i - angle_j - admittance_phase
                matrix_a[i, j] = voltage_i * voltage_j * admittance_module * np.cos(angle).real
                matrix_b[i, j] = voltage_i * voltage_j * admittance_module * np.sin(angle).real

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
        for generator in generators:
            if generator.inertia_coefficient == 0:
                # Generator has no inertia
                raise GeneratorInertiaException(generator.name)

        from_time = from_trajectory_time.time
        to_time = to_trajectory_time.time
        network_state = from_trajectory_time.network_state

        matrix_a, matrix_b = self._get_power_matrices(generators, network_state, from_time)

        derivatives_first = [generator.get_angular_speed(from_time) * self._network.pulse for generator in generators]

        derivatives_second = list()
        for i, generator in enumerate(generators):
            power_sum = generator.mechanical_power - sum(matrix_a[i])
            derivatives_second.append(power_sum * self._network.pulse / generator.inertia_coefficient)

        derivatives_third = list()
        for i, generator in enumerate(generators):
            power_sum = sum(matrix_b[i][j] * (derivatives_first[i] - derivatives_first[j])
                            for j in range(len(generators)))
            derivatives_third.append(power_sum * self._network.pulse / generator.inertia_coefficient)

        derivatives_fourth = list()
        for i, generator in enumerate(generators):
            power_sum = sum(matrix_a[i][j] * (derivatives_first[i] - derivatives_first[j]) ** 2
                            + matrix_b[i][j] * (derivatives_second[i] - derivatives_second[j])
                            for j in range(len(generators)))
            derivatives_fourth.append(power_sum * self._network.pulse / generator.inertia_coefficient)

        derivatives_fifth = list()
        for i, generator in enumerate(generators):
            power_sum = sum(3 * matrix_a[i][j]
                            * (derivatives_first[i] - derivatives_first[j])
                            * (derivatives_second[i] - derivatives_second[j])
                            + matrix_b[i][j]
                            * (derivatives_third[i] - derivatives_third[j]
                               - (derivatives_first[i] - derivatives_first[j]) ** 3)
                            for j in range(len(generators)))
            derivatives_fifth.append(power_sum * self._network.pulse / generator.inertia_coefficient)

            time_interval = to_time - from_time
            time_interval_second = time_interval * time_interval
            time_interval_third = time_interval * time_interval_second
            time_interval_fourth = time_interval * time_interval_third

            # Compute rotor angle at target time
            delta_angle = (
                time_interval * derivatives_first[i] +
                time_interval_second * derivatives_second[i] / 2 +
                time_interval_third * derivatives_third[i] / 6 +
                time_interval_fourth * derivatives_fourth[i] / 24
            )
            rotor_angle = generator.get_rotor_angle(from_time) + delta_angle
            generator.add_rotor_angle(to_time, rotor_angle)

            # Compute angular speed at target time
            delta_speed = (
                time_interval * derivatives_second[i] +
                time_interval_second * derivatives_third[i] / 2 +
                time_interval_third * derivatives_fourth[i] / 6 +
                time_interval_fourth * derivatives_fifth[i] / 24
            )
            to_angular_speed = generator.get_angular_speed(from_time) + delta_speed / self._network.pulse
            generator.add_angular_speed(to_time, to_angular_speed)

            generator.add_network_state(to_time, to_trajectory_time.network_state)
