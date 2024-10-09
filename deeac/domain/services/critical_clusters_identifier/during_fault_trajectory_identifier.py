# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import json
import cmath

from typing import List, Set, Tuple

from .identifier import GapBasedIdentifier
from deeac.domain.models import DynamicGenerator, Network, NetworkState


class DuringFaultTrajectoryCriticalClustersIdentifier(GapBasedIdentifier):
    """
    The individual trajectories are computed using Taylor Series during the fault
    Then the critical cluster is defined by the gap in angle variation
    """

    def __init__(
        self, network: Network, during_fault_identification_time_step: float, generators: Set[DynamicGenerator],
        significant_angle_variation_threshold: float = None,
        maximum_number_candidates: int = 0, min_cluster_power: float = None,
        during_fault_identification_plot_times: List = None, try_all_combinations: bool = False,
        tso_customization: str = "default", never_critical_generators: List = None
    ):
        """
        Initialize the identifier. Only generators from post-fault should be considered.
        Any generator with a criterion higher than the threshold multiplied by the maximum criterion is
        considered as critical
        :param network: Network for which the identifier must be created
        :param during_fault_identification_time_step: Time in milliseconds to compute the angle using
                                                      Taylor series to identify the critical cluster
        :param generators: Set of dynamic generators to consider
        :param significant_angle_variation_threshold: Angle in degrees (positive value expected).
                                                      Enables to detect faults that have negligible consequences
                                                      on the dynamic generators
        :param maximum_number_candidates: Maximum number of critical cluster candidates this identifier can generate
                                          A value of 0 or lower means all possible clusters. Otherwise, the returned
                                          candidates are always the ones with the least generators, in increasing size
        :param min_cluster_power: Minimum aggregated active power (per unit) a cluster must deliver to be considered a
                                  potential critical cluster candidate. If None, the aggregated power is not considered
        :param during_fault_identification_plot_times: Times in milliseconds to plot the angles using Taylor series
        :param try_all_combinations: Whether to create a new candidate cluster by removing generators one by one
                                     or to try all combinations of generators
        :param tso_customization: whether to use the default working of an identifier
        or a version meant for a specific network
        :param never_critical_generators: the generators that must be excluded from the critical cluster identification
        """
        self._during_fault_identification_time_step = during_fault_identification_time_step
        self._significant_angle_variation_threshold = significant_angle_variation_threshold
        self._during_fault_identification_plot_times = during_fault_identification_plot_times
        self._max_angle_at_dft_identification_time = 0

        super().__init__(
            network=network,
            generators=generators,
            maximum_number_candidates=maximum_number_candidates,
            min_cluster_power=min_cluster_power,
            try_all_combinations=try_all_combinations,
            tso_customization=tso_customization,
            never_critical_generators=never_critical_generators
        )

    def _get_angle_derivatives(self, matrix_a, matrix_b) -> Tuple[List, List]:
        """
        Compute the second and fourth order angle derivative
        :return: list of second order angle derivative, and list of fourth order angle derivative
        """
        # Second order derivative with matrix_a
        d2_list = list()
        for row_matrix_a, generator in zip(matrix_a, self._generators):
            d2 = self._network.pulse * (generator.mechanical_power - sum(row_matrix_a)) / generator.inertia_coefficient
            d2_list.append(d2)

        # Fourth order derivative with the second order derivative and matrix_b
        d4_list = list()
        for d2, row_matrix_b, generator in zip(d2_list, matrix_b, self._generators):
            d2_sum = sum(row_matrix_b[j] * (d2 - d2_list[j]) for j in range(len(self._generators)))
            d4 = self._network.pulse * d2_sum / generator.inertia_coefficient
            d4_list.append(d4)

        return d2_list, d4_list

    def _get_power_matrices(self) -> Tuple[List[List[float]], List[List[float]]]:
        """
        Computes the power matrices for the Taylor series angle computation
        :return: matrices pair as coefficient of the second and fourth order angle derivative respectively
        """
        matrix_a = list()
        matrix_b = list()
        for generator_i in self._generators:
            row_a = list()
            row_b = list()
            for generator_j in self._generators:
                name_i = generator_i.bus.name
                name_j = generator_j.bus.name
                admittance_module, admittance_phase = \
                    self._network.get_admittance(name_i, name_j, NetworkState.DURING_FAULT)

                delta_i = generator_i.get_rotor_angle(0)
                delta_j = generator_j.get_rotor_angle(0)
                angle = delta_i - delta_j - admittance_phase

                voltage_i = abs(generator_i.generator.internal_voltage)
                voltage_j = abs(generator_j.generator.internal_voltage)
                row_a.append(voltage_i * voltage_j * admittance_module * cmath.cos(angle).real)
                row_b.append(voltage_i * voltage_j * admittance_module * cmath.sin(angle).real)

            matrix_a.append(row_a)
            matrix_b.append(row_b)

        return matrix_a, matrix_b

    def _compute_angle_variation_list(self) -> List[float]:
        """
        Computes the variation in angle from fault time to time step for every generator
        :return: the list of all angle variation in radians
        """
        matrix_a, matrix_b = self._get_power_matrices()
        d2_list, d4_list = self._get_angle_derivatives(matrix_a, matrix_b)

        generator_variation_list = list()
        generator_taylor_angles = dict()

        # Conversion milliseconds to seconds
        t = self._during_fault_identification_time_step / 10 ** 3
        for generator, d2, d4 in zip(self._generators, d2_list, d4_list):
            generator_variation_list.append((d2 * t ** 2 / 2 + d4 * t ** 4 / 24) * 180 / cmath.pi)

            # Compute the angles for several time values if the user specified it
            if self._during_fault_identification_plot_times is not None:
                for time_step_millisecond in self._during_fault_identification_plot_times:
                    time_step = float(time_step_millisecond) / 10 ** 3
                    # Save the values in a dictionary {time_step: angle list}
                    if time_step not in generator_taylor_angles:
                        generator_taylor_angles[time_step] = list()
                    angle = (d2 * time_step ** 2 / 2 + d4 * time_step ** 4 / 24) * 180 / cmath.pi
                    generator_taylor_angles[time_step].append(angle)

        # Save the angle values if the user specified it
        if self._during_fault_identification_plot_times is not None:
            json.dump(generator_taylor_angles, open('output_taylor.json', 'w'))

        return generator_variation_list
