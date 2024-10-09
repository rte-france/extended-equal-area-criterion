# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Type, List, Set

from deeac.domain.models import Network, DynamicGenerator
from deeac.domain.services.critical_clusters_identifier import CriticalClustersIdentifier


class CriticalClustersIdentifierFactory:
    """
    Service able to generate any type of OMIB.
    """

    @staticmethod
    def get_identifier(
        network: Network, generators: Set[DynamicGenerator], cc_identifier_type: Type[CriticalClustersIdentifier],
        threshold: float = 0.5, min_cluster_power: float = None, threshold_decrement: float = 0.1,
        critical_generator_names: List[str] = None, maximum_number_candidates: int = 0, observation_moment_id: int = -1,
        during_fault_identification_time_step: float = None, during_fault_identification_plot_times: List = None,
        significant_angle_variation_threshold: float = None,
        try_all_combinations: bool = False, tso_customization: str = "default", never_critical_generators: List = None
    ) -> CriticalClustersIdentifier:
        """
        Get the specific type of critical cluster identifier.

        :param network: Network for which the identifier must be created.
        :param generators: Set of dynamic generators to consider.
        :param cc_identifier_type: Type of critical cluster identifier to use to obtain the critical and non-critical
                                    sets of generators.
        :param threshold: Threshold (between 0 and 1) used to determine the critical generators when comparing
                          criterions.
        :param min_cluster_power: Minimum aggregated active power (per unit) a cluster must deliver to be consider as a
                                  potential critical cluster candidate. If None, the aggregated power is not considered.
        :param threshold_decrement: Value to subtract to the threshold in case the critical machine candidates are not
                                    able to provide the minimum active power for the cluster. The subtraction may be
                                    performed multiple times until finding a cluster that meets the minimal aggregated
                                    power.
        :param critical_generator_names: List of the names of the generators that must be considered as critical. This
                                         parameter is only used with the constrained critical cluster identifier.
        :param maximum_number_candidates: Maximum number of critical cluster candidates the identifier can generate.
                                          A value of 0 or lower means all possible clusters. Otherwise, the returned
                                          candidates are always the ones with the least generators, in increasing size.
        :param observation_moment_id: Identifier of the observation time to consider when computing the criterions in
                                      case of a trajectory identifier. This time is a moment at which all generator
                                      angles were updated alongside their trajectory. The identifier corresponds to
                                      the update number. By default, the last update is considered (-1). A value of 0
                                      corresponds to the initial angles.
        :param during_fault_identification_time_step: Time in milliseconds to compute the angle using
                                                      Taylor series to identify the critical cluster.
        :param during_fault_identification_plot_times: Times in milliseconds to plot the angles using Taylor series.
        :param significant_angle_variation_threshold: Angle in degrees (positive value expected).
                                                      Enables to detect faults that have negligible consequences
                                                      on the dynamic generators
        :param try_all_combinations: Whether to create a new candidate cluster by removing generators one by one
                                     or to try all combinations of generators
        :param tso_customization: whether to use the default working of an identifier
        or a version meant for a specific network
        :param never_critical_generators: the generators that must be excluded from the critical cluster identification
        :return: The expected critical cluster identifier.
        """
        from deeac.domain.services.critical_clusters_identifier import (
            TrajectoryCriticalClustersIdentifier, ConstrainedCriticalClustersIdentifier,
            DuringFaultTrajectoryCriticalClustersIdentifier
        )
        if cc_identifier_type == TrajectoryCriticalClustersIdentifier:
            # Trajectory identifier requires static EEAC service
            return cc_identifier_type(
                network=network,
                generators=generators,
                maximum_number_candidates=maximum_number_candidates,
                min_cluster_power=min_cluster_power,
                try_all_combinations = try_all_combinations,
                observation_moment_id=observation_moment_id,
                tso_customization=tso_customization,
                never_critical_generators=never_critical_generators
            )
        elif cc_identifier_type == ConstrainedCriticalClustersIdentifier:
            # Constrained identifier requires critical generator names
            if critical_generator_names is None:
                critical_generator_names = []
            return cc_identifier_type(
                network=network,
                generators=generators,
                maximum_number_candidates=maximum_number_candidates,
                min_cluster_power=min_cluster_power,
                try_all_combinations = try_all_combinations,
                critical_generator_names=critical_generator_names,
                threshold_decrement=threshold_decrement,
                never_critical_generators=never_critical_generators
            )
        elif cc_identifier_type == DuringFaultTrajectoryCriticalClustersIdentifier:
            return cc_identifier_type(
                network=network,
                generators=generators,
                maximum_number_candidates=maximum_number_candidates,
                min_cluster_power=min_cluster_power,
                try_all_combinations = try_all_combinations,
                during_fault_identification_time_step=during_fault_identification_time_step,
                during_fault_identification_plot_times=during_fault_identification_plot_times,
                significant_angle_variation_threshold=significant_angle_variation_threshold,
                tso_customization=tso_customization,
                never_critical_generators=never_critical_generators
            )
        # Other identifiers
        return cc_identifier_type(
            network=network,
            generators=generators,
            maximum_number_candidates=maximum_number_candidates,
            min_cluster_power=min_cluster_power,
            try_all_combinations = try_all_combinations,
            threshold=threshold,
            threshold_decrement=threshold_decrement,
            never_critical_generators=never_critical_generators
        )
