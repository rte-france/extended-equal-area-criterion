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
from typing import Dict, Tuple, List, Iterator, Set

from deeac.domain.models import GeneratorCluster, Network, NetworkState, DynamicGenerator
from deeac.domain.exceptions import (
    CriticalClustersIdentifierThresholdException,
    CriticalClustersIdentifierInfiniteCriterionException,
    CriticalClustersIdentifierClusterException
)


class CriticalClustersIdentifier(ABC):
    """
    Identifier of critical clusters of generators.
    """

    def __init__(
        self, network: Network, generators: Set[DynamicGenerator], never_critical_generators: List = None,
        maximum_number_candidates: int = 0, min_cluster_power: float = None, try_all_combinations: bool = None
    ):
        """
        Initialize the identifier. Only generators from post-fault state should be considered.
        Any generator with a criterion higher than the threshold multiplied by the maximum criterion is
        considered as potentially critical.

        :param network: Network for which the identifier must be created.
        :param generators: Set of dynamic generators to consider.
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
        self._generators = generators
        # Set of generators to consider but never as potentially critical
        if never_critical_generators is not None:
            self._never_critical_generators = never_critical_generators
        # Can't put list() as default argument: leads to unpredictable behaviour
        else:
            self._never_critical_generators = list()

        # Initialize containers for intermediate results to improve performances
        self._generator_electric_powers: Dict[DynamicGenerator, float] = dict()
        self._generator_accelerations: Dict[DynamicGenerator, float] = dict()

        # Identify critical machine candidates
        self._critical_machine_candidates = list()

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
        if self._try_all_combinations is True:
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
        self, candidate_list: List[List[DynamicGenerator]]
    ) -> Iterator[Tuple[GeneratorCluster, GeneratorCluster]]:
        """
        Get the critical and non-critical cluster candidates.
        :return: An iterator of tuples with respectively the critical and non-critical cluster candidates.
        """
        for n, candidates in enumerate(candidate_list):
            if self._maximum_number_candidates > 0 and n >= self._maximum_number_candidates:
                # Limit reached
                break

            aggregate_power = sum(gen.active_power_pu for gen in candidates)
            if self._min_cluster_power is not None and abs(aggregate_power) < self._min_cluster_power:
                # Cluster power is too low to consider it as a candidate
                continue
            critical_generators = set(candidates)
            critical_cluster = GeneratorCluster(critical_generators)
            non_critical_cluster = GeneratorCluster(
                {generator for generator in self._generators if generator not in critical_generators}
            )
            # Return clusters
            yield critical_cluster, non_critical_cluster

    @abstractmethod
    def _identify_critical_machine_candidates(self, criterions: List[Tuple[DynamicGenerator, float]]):
        """
        Search for the set of machines that may be critical
        """
        pass


class ThresholdBasedIdentifier(CriticalClustersIdentifier):
    """
    This type of identifier uses a criterion specific to each identifier type
    and every generator with a criterion value above a certain threshold is considered critical
    """

    def __init__(
        self, network: Network, generators: Set[DynamicGenerator], threshold: float = 0.5,
        maximum_number_candidates: int = 0, min_cluster_power: float = None, threshold_decrement: float = 0.1,
        try_all_combinations: bool = False, never_critical_generators: List = None
    ):
        """
        Initialize the identifier. Only generators from post-fault state should be considered.
        Any generator with a criterion higher than the threshold multiplied by the maximum criterion is
        considered as potentially critical.

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
        if threshold <= 0 or threshold >= 1:
            raise CriticalClustersIdentifierThresholdException(threshold)

        self._threshold = threshold
        self._threshold_decrement = threshold_decrement
        super().__init__(
            network=network,
            generators=generators,
            maximum_number_candidates=maximum_number_candidates,
            min_cluster_power=min_cluster_power,
            try_all_combinations=try_all_combinations,
            never_critical_generators=never_critical_generators
        )

        # Compute criterions
        criterions = self._compute_criterions()
        self._identify_critical_machine_candidates(criterions)

    @abstractmethod
    def _compute_criterions(self) -> List[Tuple[DynamicGenerator, float]]:
        """
        Compute the criterion for each generator.

        :return: List of tuples (generator, criterion) associating each generator to its criterion.
        """
        pass

    def _get_generator_initial_electric_power(self, generator: DynamicGenerator) -> float:
        """
        Compute the initial electric power of a generator.

        :param generator: The generator for which the electric power must be computed.
        :return: The generator initial electric power.
        """
        if generator in self._generator_electric_powers:
            # Electric power already computed
            return self._generator_electric_powers[generator]

        electric_power = 0
        for other_generator in self._generators:
            # Get product of internal voltages
            voltage_product = self._network.get_generator_voltage_amplitude_product(
                generator.name,
                other_generator.name
            )
            # Compute admittance amplitude in during-fault state
            admittance_amplitude, admittance_angle = self._network.get_admittance(
                generator.bus.name,
                other_generator.bus.name,
                NetworkState.DURING_FAULT
            )
            cosine = np.cos(generator.get_rotor_angle(0) - other_generator.get_rotor_angle(0) - admittance_angle)
            electric_power += voltage_product * admittance_amplitude * cosine

        # Store and return electric power
        self._generator_electric_powers[generator] = electric_power
        return electric_power

    def _get_generator_initial_acceleration(self, generator: DynamicGenerator):
        """
        Compute the initial acceleration of a generator.

        :param generator: Generator for which the acceleration must be computed.
        :return: The initial acceleration of the generator.
        """
        if generator in self._generator_accelerations:
            # Acceleration already computed
            return self._generator_accelerations[generator]

        # Get initial electric power
        electric_power = self._get_generator_initial_electric_power(generator)
        # Compute difference between mechanical and electric powers
        power_diff = generator.mechanical_power - electric_power
        # Compute acceleration
        acceleration = self._network.pulse * power_diff / generator.inertia_coefficient

        # Store and return acceleration
        self._generator_accelerations[generator] = acceleration

        return acceleration

    def _identify_critical_machine_candidates(self, criterions: List[Tuple[DynamicGenerator, float]]):
        """
        Search for the set of machines that may be critical.
        Any generator with a criterion higher than the threshold multiplied by the maximum criterion is
        considered as a candidate to be critical.

        :param: List of tuples (generator, criterion) associating each generator to its criterion.
        This list is sorted by increasing values of the criterions.
        """
        # Discard generators that cannot be critical and sort absolute values of the criterions
        abs_criterions = [(criterion[0], abs(criterion[1])) for criterion in criterions]
        selected_criterions = [
            criterion for criterion in sorted(abs_criterions, key=lambda crit: crit[1])
        ]

        # Number of generators that may be considered
        number_generators = len(self._generators)
        # Get maximum criterion
        max_criterion = max(selected_criterions, key=lambda criterion: criterion[1])[1]
        if np.isinf(max_criterion):
            raise CriticalClustersIdentifierInfiniteCriterionException()

        # Identify the cluster candidates
        while len(self._critical_machine_candidates) < number_generators:
            # Compute the minimum critical criterion value
            min_critical_criterion = self._threshold * max_criterion
            # Get critical machine candidates whose criterion is higher than the minimum critical criterion
            self._critical_machine_candidates = [
                generator for generator, criterion in selected_criterions
                if (criterion > min_critical_criterion and generator.name not in self._never_critical_generators)
            ]

            if self._min_cluster_power is None:
                # No filter based on the aggregated power
                return

            # Compute the delivered aggregated active power
            aggregate_power = abs(sum(gen.active_power_pu for gen in self._critical_machine_candidates))
            if aggregate_power >= self._min_cluster_power:
                # The cluster is valid and verifies the condition on the aggregate power
                return
            # Decrement the threshold value
            self._threshold -= self._threshold_decrement


class GapBasedIdentifier(CriticalClustersIdentifier):
    """
    This identifier type is base on the trajectory of every generator.
    The angle variation are considered at a certain time, and all the generators beyond the widest absolute gap
    (compared to the generators with the closest values) in angle variation are considered critical
    """

    def __init__(
        self, network: Network, generators: Set[DynamicGenerator], tso_customization: str = "default",
        never_critical_generators: List = None, try_all_combinations: bool = None,
        maximum_number_candidates: int = 0, min_cluster_power: float = None
    ):
        """
        Initialize the identifier. Only generators from post-fault should be considered.
        Any generator with a criterion higher than the threshold multiplied by the maximum criterion is
        considered as critical.

        :param network: Network for which the identifier must be created.
        :param generators: Set of dynamic generators to consider.
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
            generators=generators,
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

    def _identify_from_list(self, generator_variation_list, generator_list) -> List:
        """

        """
        # The order of the generators must be kept as is
        ordered_index = np.argsort(generator_variation_list)
        gaps = list()
        for n, m in zip(ordered_index[:-1], ordered_index[1:]):
            gaps.append(generator_variation_list[m] - generator_variation_list[n])

        absolute_gaps = [abs(gap) for gap in gaps]
        # The critical machines are defined as the one beyond the widest angle gap compared to its neighbour
        index_largest_absolute_gap = np.argmax(absolute_gaps)

        critical_machine_candidates = list()

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

    def _identify_critical_machine_candidates(self, generator_variation_list):
        """
        Search for the set of machines that may be critical.
        Computes the angle at a certain point in time after the fault using Taylor series
        The generators beyond the widest angle gap relatively to their ordering neighbour are considered critical
        :param generator_variation_list: angle variations between t0 and a specified time for every generator
        """

        generator_list = list()
        variation_list = list()
        for generator, angle in zip(self._generators, generator_variation_list):
            
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

            generator_list.append(generator)
            variation_list.append(angle)

        if len(generator_list) == 0:
            raise CriticalClustersIdentifierClusterException

        self._max_angle_at_dft_identification_time = abs(max(variation_list))
        self._critical_machine_candidates = self._identify_from_list(variation_list, generator_list)
