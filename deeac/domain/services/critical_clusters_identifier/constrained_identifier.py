# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Dict, Tuple, List, Iterator, Set

from .identifier import CriticalClustersIdentifier
from deeac.domain.models import Network, DynamicGenerator
from deeac.domain.exceptions import CriticalClustersIdentifierUnknownGeneratorsException

from deeac.domain.models import GeneratorCluster


class ConstrainedCriticalClustersIdentifier(CriticalClustersIdentifier):
    """
    Identifier of a critical cluster of generators constrained by the user.
    """

    def __init__(
        self,
        network: Network,
        generators: Set[DynamicGenerator],
        critical_generator_names: List[str]
    ):
        """
        Initialize the identifier.

        :param network: Network for which the identifier must be created.
        :param generators: Set of dynamic generators to consider.
        :param critical_generator_names: Names of all the generators that must be considered as critical.
                                         This list must be ordered in increasing order of criticality.
                                         The other generators are considered as not critical.
        :raises UnknownGeneratorsException if one or several critical generators cannot be identified.
        """
        self._critical_generator_names = critical_generator_names

        super().__init__(
            network=network,
            generators=generators
        )

        # Compute criterions
        criterions = self._compute_criterions()
        self._identify_critical_machine_candidates(criterions)

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

    @property
    def candidate_clusters(self) -> Iterator[Tuple[GeneratorCluster, GeneratorCluster]]:
        """
        Get the critical and non-critical cluster candidates.

        :return: An iterator of tuples with respectively the critical and non-critical cluster candidates.
        """
        candidate_list = [self._critical_machine_candidates]
        return self._get_candidate_cluster(candidate_list)

    def _identify_critical_machine_candidates(self, criterions: List[Tuple[DynamicGenerator, float]]):
        """
        Search for the set of machines that may be critical
        """
        self._critical_machine_candidates = [
            generator for generator, criterion in criterions
            if criterion == 1
        ]
