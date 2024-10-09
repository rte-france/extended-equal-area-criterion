# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List, Tuple, Set

from .identifier import ThresholdBasedIdentifier
from deeac.domain.models import Network, DynamicGenerator
from deeac.domain.exceptions import CriticalClustersIdentifierUnknownGeneratorsException


class ConstrainedCriticalClustersIdentifier(ThresholdBasedIdentifier):
    """
    Identifier of a critical cluster of generators constrained by the user.
    """

    def __init__(
        self, network: Network, generators: Set[DynamicGenerator], critical_generator_names: List[str],
        maximum_number_candidates: int = 0, min_cluster_power: float = None,
        threshold_decrement: float = 0.1, try_all_combinations: bool = False, never_critical_generators: List = None
    ):
        """
        Initialize the identifier.

        :param network: Network for which the identifier must be created.
        :param generators: Set of dynamic generators to consider.
        :param critical_generator_names: Names of all the generators that must be considered as critical.
                                         This list must be ordered in increasing order of criticality.
                                         The other generators are considered as not critical.
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
        :raises UnknownGeneratorsException if one or several critical generators cannot be identified.
        """
        # Keep critical generator names
        self._critical_generator_names = critical_generator_names

        # Call parent constructor
        super().__init__(
            network=network,
            generators=generators,
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
        criterions = []
        # Generate generator sets with criterion values
        remaining_generator_names = set()
        critical_generators = set()
        for generator_name in self._critical_generator_names:
            try:
                generator = next(generator for generator in self._generators if generator.name == generator_name)
                critical_generators.add(generator)
                criterions.append((generator, 1))
            except StopIteration:
                # Generator not found
                remaining_generator_names.add(generator_name)

        # Check if unknown generators remain
        if remaining_generator_names:
            raise CriticalClustersIdentifierUnknownGeneratorsException(self._generators, remaining_generator_names)

        for generator in self._generators:
            if generator not in critical_generators:
                criterions.append((generator, 0))

        return criterions
