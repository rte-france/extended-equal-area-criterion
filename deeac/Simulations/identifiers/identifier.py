"""
Module for identifier.

:module: identifier
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import itertools

import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Tuple, List, Iterator


from deeac.Models.generator import Generator
from deeac.Models.generator_snapshot import GeneratorSnapshot
from deeac.Models.generator_cluster import GeneratorCluster
from deeac.Models.network import Network


class CriticalClustersIdentifier(ABC):
    """
    Criticalclustersidentifier.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar network: network.
    :ivar generators: generators.
    :ivar never_critical_generators: never critical generators.
    :ivar maximum_number_candidates: maximum number candidates.
    :ivar min_cluster_power: min cluster power.
    :ivar try_all_combinations: try all combinations.
    """

    def __init__(
        self,
        network: Network,
        generator_snapshot: GeneratorSnapshot,
        never_critical_generators: List = None,
        maximum_number_candidates: int = 0,
        min_cluster_power: float = None,
        try_all_combinations: bool = None,
    ):
        """
        Initialize the identifier. Only generators from post-fault state should be considered.
        Any generator with a criterion higher than the threshold multiplied by the maximum criterion is
        considered as potentially critical.
        
        :param network: Network for which the identifier must be created.
        :param generator_snapshot: Generator snapshot to consider.
        :param never_critical_generators: generators that must be excluded from the critical cluster identification
        :param maximum_number_candidates: Maximum number of critical cluster candidates this identifier can generate.
        A value of 0 or lower means all possible clusters. Otherwise, the returned
        candidates are always the ones with the least generators, in increasing size.
        :param min_cluster_power: Minimum aggregated active power (per unit) a cluster must deliver to be considered as a
        potential critical cluster candidate. If None, the aggregated power is not considered.
        :param try_all_combinations: Whether to create a new candidate cluster by removing generators one by one
        or to try all combinations of generators
        """
        self._network = network
        self._maximum_number_candidates = maximum_number_candidates
        self._min_cluster_power = min_cluster_power
        self._try_all_combinations = try_all_combinations

        # Set of generators to consider
        self._generator_snapshot = generator_snapshot
        self._generators: List[Generator] = list(generator_snapshot.generators)
        self._generator_indices = list(range(len(self._generators)))
        # Set of generators to consider but never as potentially critical
        if never_critical_generators is not None:
            self._never_critical_generators = never_critical_generators
        # Can't put list() as default argument: leads to unpredictable behaviour
        else:
            self._never_critical_generators = list()

        # Initialize containers for intermediate results to improve performances
        self._generator_electric_powers: Dict[Generator, float] = dict()
        self._generator_accelerations: Dict[Generator, float] = dict()

        # Identify critical machine candidates
        self._critical_machine_candidates: List[int] = []

    @property
    def candidate_clusters(self) -> Iterator[Tuple[GeneratorCluster, GeneratorCluster]]:
        """
        Get the critical and non-critical cluster candidates.
        This function produces an iterator of cluster pairs, containing each respectively the critical and non critical
        cluster candidates.
        The iterator will start with the largest set, and then decrease its size by one at each step.
        The element subtracted from the set at each step is the one with the lowest criterion value.
        
        It can also run all the combination if try_all_combination is set at true in the CCI node configuration
        
        :return: An iterator of tuples with respectively the critical and non-critical cluster candidates.
        """
        # Generate every new candidate by getting a new generator combination
        if self._try_all_combinations:
            candidate_list = [
                list(combination) for n in range(1, len(self._critical_machine_candidates) + 1)
                for combination in itertools.combinations(self._critical_machine_candidates, n)
            ]
            candidate_list.reverse()
            return self._get_candidate_cluster(candidate_list)
        # Generate every new candidate by removing a generator (default)
        else:
            candidate_list = [
                self._critical_machine_candidates[iteration:]
                for iteration in range(len(self._critical_machine_candidates))
            ]
            candidate_list.reverse()
            return self._get_candidate_cluster(candidate_list)

    def _get_candidate_cluster(
        self, candidate_list: List[List[int]]
    ) -> Iterator[Tuple[GeneratorCluster, GeneratorCluster]]:
        """
        Get the critical and non-critical cluster candidates.
        :return: An iterator of tuples with respectively the critical and non-critical cluster candidates.
        """
        for n, candidates in enumerate(candidate_list):
            if 0 < self._maximum_number_candidates <= n:
                # Limit reached
                break

            aggregate_power = float(
                np.sum(self._generator_snapshot.mechanical_powers[candidates])
            )
            if self._min_cluster_power is not None and abs(aggregate_power) < self._min_cluster_power:
                # Cluster power is too low to consider it as a candidate
                continue
            critical_cluster = GeneratorCluster(self._generator_snapshot, candidates)
            non_critical_indices = [idx for idx in self._generator_indices if idx not in candidates]
            non_critical_cluster = GeneratorCluster(self._generator_snapshot, non_critical_indices)
            # Return clusters
            yield critical_cluster, non_critical_cluster

    @abstractmethod
    def _identify_critical_machine_candidates(self, criterions: List[Tuple[int, float]]):
        """
        identify critical machine candidates.
        
        :param criterions: criterions.
        """
        pass




class GapBasedIdentifier(CriticalClustersIdentifier):
    """
    Gapbasedidentifier.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar network: network.
    :ivar generators: generators.
    :ivar tso_customization: tso customization.
    :ivar never_critical_generators: never critical generators.
    :ivar try_all_combinations: try all combinations.
    :ivar maximum_number_candidates: maximum number candidates.
    :ivar min_cluster_power: min cluster power.
    """

    def __init__(
        self, network: Network, generator_snapshot: GeneratorSnapshot, tso_customization: str = "default",
        never_critical_generators: List = None, try_all_combinations: bool = None,
        maximum_number_candidates: int = 0, min_cluster_power: float = None
    ):
        """
        Initialize the identifier. Only generators from post-fault should be considered.
        Any generator with a criterion higher than the threshold multiplied by the maximum criterion is
        considered as critical.
        
        :param network: Network for which the identifier must be created.
        :param generator_snapshot: Generator snapshot to consider.
        :param never_critical_generators: generators that must be excluded from the critical cluster identification
        :param maximum_number_candidates: Maximum number of critical cluster candidates this identifier can generate.
        A value of 0 or lower means all possible clusters. Otherwise, the returned
        candidates are always the ones with the least generators, in increasing size.
        :param min_cluster_power: Minimum aggregated active power (per unit) a cluster must deliver to be consider as a
        potential critical cluster candidate. If None, the aggregated power is not considered.
        :param try_all_combinations: Whether to create a new candidate cluster by removing generators one by one
        or to try all combinations of generators
        """

        self._generator_taylor_angles = dict()
        super().__init__(
            network=network,
            generator_snapshot=generator_snapshot,
            maximum_number_candidates=maximum_number_candidates,
            min_cluster_power=min_cluster_power,
            try_all_combinations=try_all_combinations,
            never_critical_generators=never_critical_generators
        )
        self._tso_customization = tso_customization.upper()

        generator_variation_list = self._compute_angle_variation_list()
        self._identify_critical_machine_candidates(generator_variation_list)

    @abstractmethod
    def _compute_angle_variation_list(self) -> List[float]:
        """
        Compute the angles at a certain time for each generator
        :return: angle list computed by Taylor Series
        """
        pass

    def _identify_from_list(
        self,
        generator_variation_list: List[float],
        generator_list: List[int],
    ) -> List[int]:
        """
        identify from list.
        
        :param generator_variation_list: generator variation list.
        :param generator_list: generator list.
        """
        ordered_index = list(np.argsort(generator_variation_list, kind="stable"))
        # Deterministic tie-break for equal variations: use generator names.
        tie_tolerance = 1e-9
        start = 0
        while start < len(ordered_index):
            end = start + 1
            start_value = generator_variation_list[ordered_index[start]]
            while end < len(ordered_index):
                value = generator_variation_list[ordered_index[end]]
                if abs(value - start_value) > tie_tolerance:
                    break
                end += 1
            if end - start > 1:
                tie_block = ordered_index[start:end]
                tie_block.sort(
                    key=lambda idx: self._generators[generator_list[idx]].name,
                    reverse=True,
                )
                ordered_index[start:end] = tie_block
            start = end
        gaps = list()
        for n, m in zip(ordered_index[:-1], ordered_index[1:]):
            gaps.append(generator_variation_list[m] - generator_variation_list[n])

        absolute_gaps = [abs(gap) for gap in gaps]
        # The critical machines are defined as the one beyond the widest angle gap compared to its neighbour
        index_largest_absolute_gap = np.argmax(absolute_gaps)

        critical_machine_candidates: List[int] = list()

        # If the angle where the gap is the widest gap is negative (backswing)
        if generator_variation_list[ordered_index[index_largest_absolute_gap]] < 0:
            # then we keep the angle on the left side of the list
            for n in ordered_index[:index_largest_absolute_gap + 1]:
                critical_machine_candidates.append(generator_list[n])
            return critical_machine_candidates[::-1]
        # otherwise keep the machines on the right side of the list
        else:
            for n in ordered_index[index_largest_absolute_gap + 1:]:
                critical_machine_candidates.append(generator_list[n])
            return critical_machine_candidates

    def _identify_critical_machine_candidates(self, generator_variation_list: List[float]) -> None:
        """
        Search for the set of machines that may be critical.
        Computes the angle at a certain point in time after the fault using Taylor series
        The generators beyond the widest angle gap relatively to their ordering neighbour are considered critical
        :param generator_variation_list: angle variations between t0 and a specified time for every generator
        """

        generator_list: List[int] = list()
        variation_list = list()
        for index, (generator, angle) in enumerate(zip(self._generators, generator_variation_list)):
            
            # Ignore the generators specified to be never critical
            if generator.name in self._never_critical_generators:
                continue

            # Ignore the small hydro units if "RTE" is specified as tso_customization in the first identification
            if (self._tso_customization == "NO_HYDRO"
                    and generator.source.value == "HYDRO" and abs(generator.max_active_power_pu) < 1):
                continue

            # Ignore the non-nuclear units if "RTE" is specified as tso_customization in the second identification
            if self._tso_customization == "NUCLEAR" and generator.source.value != "NUCLEAR":
                continue

            generator_list.append(index)
            variation_list.append(angle)

        if len(generator_list) == 0:
            raise ValueError("No generator remains after the critical-cluster source filters were applied.")

        self._max_angle_at_dft_identification_time = abs(max(variation_list))
        self._critical_machine_candidates = self._identify_from_list(variation_list, generator_list)
