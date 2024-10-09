# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from numpy import finfo
from typing import Dict, Tuple, List, Set

from .identifier import ThresholdBasedIdentifier
from deeac.domain.models import DynamicGenerator, Bus, Network, NetworkState
from deeac.domain.models.matrices import ImpedanceMatrix
from deeac.domain.exceptions import CompositeCriterionException


class CompositeCriticalClustersIdentifier(ThresholdBasedIdentifier):
    """
    Identifier of critical clusters of generators based on the composite criterion.
    """

    def __init__(
        self, network: Network, generators: Set[DynamicGenerator], threshold: float = 0.5,
        maximum_number_candidates: int = 0, min_cluster_power: float = None,
        threshold_decrement: float = 0.1, try_all_combinations: bool = False, never_critical_generators: List = None
    ):
        """
        Initialize the identifier. Only generators from post-fault should be considered.
        Any generator with a criterion higher than the threshold multiplied by the maximum criterion is
        considered as critical.

        :param network: Network for which the identifier must be created.
        :param generators: Set of dynamic generators to consider.
        :param threshold: Threshold (between 0 and 1) used to determine the critical generators when comparing
                          criterions.
        :param maximum_number_candidates: Maximum number of critical cluster candidates this identifier can generate.
                                          A value of 0 or lower means all possible clusters. Otherwise, the returned
                                          candidates are always the ones with the least generators, in increasing size.
        :param min_cluster_power: Minimum aggregated active power (per unit) a cluster must deliver to be consider as a
                                  potential critical cluster candidate. If None, the aggregated power is not considered.
        :param threshold_decrement: Value to subtract to the threshold in case the critical machine candidates are not
                                    able to provide the minimum active power for the cluster. The subtraction may be
                                    performed multiple times until finding a cluster that meets the minimal aggregated
                                    power.
        :param try_all_combinations: Whether to create a new candidate cluster by removing generators one by one
                                     or to try all combinations of generators
        :param never_critical_generators: the generators that must be excluded from the critical cluster identification
        """
        if len(network.failure_events) > 1:
            # Composite criterion can be applied in a network with a single failure only.
            raise CompositeCriterionException()

        # Containers to store intermediate results
        self._generator_pre_fault_distances: Dict[DynamicGenerator, float] = dict()
        self._generator_post_fault_distances: Dict[DynamicGenerator, float] = dict()

        super().__init__(
            network=network,
            generators=generators,
            threshold=threshold,
            maximum_number_candidates=maximum_number_candidates,
            min_cluster_power=min_cluster_power,
            threshold_decrement=threshold_decrement,
            try_all_combinations=try_all_combinations,
            never_critical_generators=never_critical_generators

        )

    def _compute_criterions(self) -> List[Tuple[DynamicGenerator, float]]:
        """
        Compute the criterion for each generator.

        :return: List of tuples (generator, criterion) associating each generator to its criterion.
        """
        # Get admittance matrices
        pre_fault_admittance_matrix = self._network.get_state(NetworkState.PRE_FAULT).admittance_matrix
        post_fault_admittance_matrix = self._network.get_state(NetworkState.POST_FAULT).admittance_matrix
        # Compute impedance matrices
        pre_fault_impedance_matrix = ImpedanceMatrix(pre_fault_admittance_matrix)
        post_fault_impedance_matrix = ImpedanceMatrix(post_fault_admittance_matrix)

        # Bus closest to the failure
        failure_bus = self._network.failure_events[0].get_nearest_bus(self._network.get_state(NetworkState.PRE_FAULT))

        # Compute composite criterion for each generator
        criterions = []
        for generator in self._generators:
            # Get generator acceleration
            acceleration = self._get_generator_initial_acceleration(generator)
            # Get electrical distances to fault
            pre_fault_distance = self._get_generator_distance_to_fault(
                generator,
                failure_bus,
                pre_fault_impedance_matrix
            )
            post_fault_distance = self._get_generator_distance_to_fault(
                generator,
                failure_bus,
                post_fault_impedance_matrix
            )
            distance = pre_fault_distance + post_fault_distance
            if distance == 0:
                # Add epsilon to avoid infinite values when computing criterion
                distance += finfo(float).eps
            # Compute criterion
            criterions.append((generator, acceleration / distance))

        return criterions

    def _get_generator_distance_to_fault(
        self, generator: DynamicGenerator, failure_bus: Bus, impedance_matrix: ImpedanceMatrix
    ) -> complex:
        """
        Get the electrical distance of a generator to the fault.

        param generator: Generator for which the distance must be computed.
        param failure_bus: Closest bus to the failure.
        param impedance_matrix: Impedance matrix to use to compute the distance.
        """
        return (
            abs(impedance_matrix[generator.bus.name, generator.bus.name]) +
            abs(impedance_matrix[failure_bus.name, failure_bus.name]) -
            2 * abs(impedance_matrix[generator.bus.name, failure_bus.name])
        )
