# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List, Set

from .identifier import GapBasedIdentifier
from deeac.domain.models import DynamicGenerator, Network


class TrajectoryCriticalClustersIdentifier(GapBasedIdentifier):
    """
    Identifier of a critical cluster of generators based on the evolution of their rotor angle along a near-critically
    cleared trajectory.
    """

    def __init__(
        self, network: Network, generators: Set[DynamicGenerator], maximum_number_candidates: int = 0,
        min_cluster_power: float = None, observation_moment_id: int = -1, try_all_combinations: bool = False,
        tso_customization: str = "default", never_critical_generators: List = None
    ):
        """
        Initialize the identifier.

        :param network: Network for which the identifier must be created.
        :param generators: Set of dynamic generators to consider.
        :param maximum_number_candidates: Maximum number of critical cluster candidates this identifier can generate.
                                          A value of 0 or lower means all possible clusters. Otherwise, the returned
                                          candidates are always the ones with the least generators, in increasing size.
        :param min_cluster_power: Minimum aggregated active power (per unit) a cluster must deliver to be consider as a
                                  potential critical cluster candidate. If None, the aggregated power is not considered.
        :param observation_moment_id: Identifier of the observation time to consider when computing the criterions.
                                      This time is a moment at which all generator angles were updated alongside their
                                      trajectory. The identifier corresponds to the update number. By default, the
                                      last update is considered (-1). A value of 0 corresponds to the initial angles.
        :param try_all_combinations: Whether to create a new candidate cluster by removing generators one by one
                                     or to try all combinations of generators
        :param tso_customization: whether to use the default working of an identifier
        or a version meant for a specific network
        :param never_critical_generators: the generators that must be excluded from the critical cluster identification
        """
        self._observation_moment_id = observation_moment_id
        super().__init__(
            network=network,
            generators=generators,
            maximum_number_candidates=maximum_number_candidates,
            min_cluster_power=min_cluster_power,
            try_all_combinations=try_all_combinations,
            tso_customization=tso_customization,
            never_critical_generators=never_critical_generators
        )

    def _compute_angle_variation_list(self):
        """
        Search for the set of machines that may be critical.
        Computes the angle at a certain point in time after the fault using Taylor series
        The generators beyond the widest angle gap relatively to their ordering neighbour are considered critical
        """
        # Get time corresponding to observation moment ID.
        observation_time = next(iter(self._generators)).observation_times[self._observation_moment_id]
        # Get observation angles gaps since fault time
        generator_variation_list = [
            generator.get_rotor_angle(observation_time) - generator.get_rotor_angle(0) for generator in self._generators
        ]
        return generator_variation_list
