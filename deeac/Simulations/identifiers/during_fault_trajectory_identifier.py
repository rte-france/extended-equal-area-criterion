"""
Module for during_fault_trajectory_identifier.

:module: during_fault_trajectory_identifier
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import json

from typing import List, Tuple, Optional
from math import pi
import numpy as np

from deeac.Simulations.identifiers.identifier import GapBasedIdentifier

from deeac.Models.generator import Generator
from deeac.Models.generator_snapshot import GeneratorSnapshot
from deeac.Models.network import Network, NetworkComputed, NetworkState

class DuringFaultTrajectoryCriticalClustersIdentifier(GapBasedIdentifier):
    """
    Identify critical-cluster candidates from the early during-fault generator trajectories.

    Rationale:
        This class implements the first EEAC decision step: reduce the full set of
        post-fault generators to a small ordered list of plausible critical-cluster
        candidates.

        The identifier does not integrate the full non-linear machine trajectories.
        Instead, it approximates the rotor-angle variation of every post-fault
        generator at one short observation time during the fault by means of a
        Taylor expansion. The coefficients of that expansion are computed from the
        during-fault reduced admittance matrix, the generator internal voltages,
        the mechanical powers, and the inertia coefficients.

        Once one scalar angle variation is available for each generator, the
        generators are ordered by that variation and the widest angular gap is
        used as the split point between the candidate critical group and the
        candidate non-critical group. The base class then turns that ordered set
        of critical generators into one or more cluster candidates.

        In the current simplified DEEAC implementation, this is the only
        identifier path used by the execution plan. Downstream OMIB, EAC, and
        selector stages depend on the candidate order produced here, so this
        class has a direct impact on both numerical results and warning messages
        about failed candidates.

    :ivar _computed: Computed network cache containing the pre-fault, during-fault,
        and post-fault simplified-network views needed by the identifier.
    :ivar _snapshot_generators: Post-fault generators considered by the identifier.
        Their order defines the correspondence between the snapshot arrays and the
        generator objects.
    :ivar _snapshot_rotor_angles: Rotor angles of ``_snapshot_generators`` at the
        post-fault reference state.
    :ivar _snapshot_voltages: Internal-voltage magnitudes of
        ``_snapshot_generators``.
    :ivar _snapshot_mechanical_powers: Mechanical powers of
        ``_snapshot_generators``.
    :ivar _snapshot_inertia_coefficients: Inertia coefficients of
        ``_snapshot_generators``.
    :ivar _snapshot_bus_names: Bus names associated with
        ``_snapshot_generators``. They are used to extract the correct rows and
        columns from the reduced admittance matrix.
    :ivar _during_fault_identification_time_step: Observation time, in
        milliseconds, at which the Taylor approximation is evaluated.
    :ivar _significant_angle_variation_threshold: Optional threshold, in degrees,
        below which the disturbance is considered too small to justify multiple
        cluster candidates.
    :ivar _during_fault_identification_plot_times: Optional list of additional
        times, in milliseconds, at which Taylor-approximated angles may be dumped
        for debugging.
    :ivar _max_angle_at_dft_identification_time: Maximum absolute angular
        variation observed at the identification time. It is used later to decide
        whether the disturbance is significant enough.
    """

    def __init__(
        self,
        network: Network,
        computed: NetworkComputed,
        during_fault_identification_time_step: float,
        generator_snapshot: GeneratorSnapshot,
        significant_angle_variation_threshold: Optional[float] = None,
        maximum_number_candidates: int = 0,
        min_cluster_power: Optional[float] = None,
        during_fault_identification_plot_times: Optional[List[float]] = None,
        try_all_combinations: bool = False,
        tso_customization: str = "default",
        never_critical_generators: Optional[List[str]] = None,
    ):
        """
        Initialize the identifier. Only generators from post-fault should be considered.
        Any generator with a criterion higher than the threshold multiplied by the maximum criterion is
        considered as critical
        :param network: Network for which the identifier must be created
        :param computed: computed network cache.
        :param during_fault_identification_time_step: Time in milliseconds to compute the angle using
        Taylor series to identify the critical cluster
        :param generator_snapshot: Generator snapshot to consider
        :param significant_angle_variation_threshold: Angle in degrees (positive value expected).
        Enables to detect faults that have negligible consequences
        on the generators
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
        self._computed = computed
        self._snapshot_generators: List[Generator] = list(generator_snapshot.generators)
        (
            self._snapshot_rotor_angles,
            self._snapshot_voltages,
            self._snapshot_mechanical_powers,
            self._snapshot_inertia_coefficients,
            self._snapshot_bus_names,
        ) = self._build_generator_snapshot(self._snapshot_generators)
        self._during_fault_identification_time_step = during_fault_identification_time_step
        self._significant_angle_variation_threshold = significant_angle_variation_threshold
        self._during_fault_identification_plot_times = during_fault_identification_plot_times
        self._max_angle_at_dft_identification_time = 0

        super().__init__(
            network=network,
            generator_snapshot=generator_snapshot,
            maximum_number_candidates=maximum_number_candidates,
            min_cluster_power=min_cluster_power,
            try_all_combinations=try_all_combinations,
            tso_customization=tso_customization,
            never_critical_generators=never_critical_generators
        )

    @staticmethod
    def _build_generator_snapshot(
        generators: List[Generator],
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[str]]:
        """
        Build array snapshots for generator data.
        
        :param generators: Generators to snapshot.
        :return: Rotor angles, voltages, mechanical powers, inertia coefficients, bus names.
        :rtype: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[str]]
        """
        rotor_angles = np.array([gen.rotor_angle for gen in generators], dtype=float)
        voltages = np.array([abs(gen.internal_voltage) for gen in generators], dtype=float)
        mechanical_powers = np.array([gen.mechanical_power for gen in generators], dtype=float)
        inertia_coefficients = np.array([gen.inertia_coefficient for gen in generators], dtype=float)
        bus_names = [gen.bus.name for gen in generators]
        return rotor_angles, voltages, mechanical_powers, inertia_coefficients, bus_names

    def _get_angle_derivatives(
        self,
        matrix_a: np.ndarray,
        matrix_b: np.ndarray,
        mechanical_powers: np.ndarray,
        inertia_coefficients: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute the second and fourth order angle derivative
        :return: numpy arrays for second order angle derivative, and fourth order angle derivative
        """
        d2_list = self._network.pulse * (mechanical_powers - matrix_a.sum(axis=1)) / inertia_coefficients
        d2_diff = d2_list[:, None] - d2_list
        d4_list = self._network.pulse * np.sum(matrix_b * d2_diff, axis=1) / inertia_coefficients

        return d2_list, d4_list

    def _get_generator_arrays(
        self,
    ) -> Tuple[List[Generator], np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[str]]:
        """
        get generator arrays.
        
        :return: Return value.
        :rtype: Tuple[List[Generator], np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[str]]
        """
        return (
            list(self._snapshot_generators),
            self._snapshot_rotor_angles,
            self._snapshot_voltages,
            self._snapshot_mechanical_powers,
            self._snapshot_inertia_coefficients,
            self._snapshot_bus_names,
        )

    def _get_power_matrices(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Computes the power matrices for the Taylor series angle computation
        :return: matrices pair as coefficient of the second and fourth order angle derivative respectively
        """
        generators, rotor_angles, voltages, mechanical_powers, inertia_coefficients, bus_names = self._get_generator_arrays()
        nb_generators = len(generators)
        matrix_a = np.zeros((nb_generators, nb_generators))
        matrix_b = np.zeros((nb_generators, nb_generators))

        for i in range(nb_generators):
            delta_i = rotor_angles[i]
            voltage_i = voltages[i]
            bus_i = bus_names[i]
            for j in range(nb_generators):
                bus_j = bus_names[j]
                admittance_module, admittance_phase = self._network.get_admittance(
                    computed=self._computed,
                    bus1_name=bus_i,
                    bus2_name=bus_j,
                    state=NetworkState.DURING_FAULT,
                )
                angle = delta_i - rotor_angles[j] - admittance_phase
                matrix_a[i, j] = voltage_i * voltages[j] * admittance_module * np.cos(angle)
                matrix_b[i, j] = voltage_i * voltages[j] * admittance_module * np.sin(angle)

        return matrix_a, matrix_b, mechanical_powers, inertia_coefficients

    def _compute_angle_variation_list(self) -> np.ndarray:
        """
        Computes the variation in angle from fault time to time step for every generator
        :return: the list of all angle variation in radians
        """
        matrix_a, matrix_b, mechanical_powers, inertia_coefficients = self._get_power_matrices()
        d2_list, d4_list = self._get_angle_derivatives(
            matrix_a, matrix_b, mechanical_powers, inertia_coefficients
        )
        t = self._during_fault_identification_time_step / 1000

        generator_variation_list = (d2_list * t ** 2 / 2 + d4_list * t ** 4 / 24) * 180 / pi

        if self._during_fault_identification_plot_times is not None:
            generator_taylor_angles = {}
            plot_times_seconds = np.array(self._during_fault_identification_plot_times) / 1000
            for time_step in plot_times_seconds:
                angles_at_time_step = (d2_list * time_step ** 2 / 2 + d4_list * time_step ** 4 / 24) * 180 / pi
                generator_taylor_angles[time_step] = angles_at_time_step.tolist()

            json.dump(generator_taylor_angles, open('output_taylor.json', 'w'))

        return generator_variation_list

    def max_angle_at_identification_time(self) -> float:
        """
        Max angle at identification time.
        
        :return: Return value.
        :rtype: float
        """
        return float(self._max_angle_at_dft_identification_time)
