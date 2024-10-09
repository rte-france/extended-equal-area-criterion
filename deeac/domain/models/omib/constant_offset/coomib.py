# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import DefaultDict, Dict
from collections import defaultdict

from deeac.domain.models import GeneratorCluster, Network, NetworkState
from deeac.domain.models.omib import OMIB
from deeac.domain.exceptions import GeneratorClusterMemberException


class COOMIB(OMIB):
    """
    Class modeling a Constant-Offset One Machine Infinite Bus (COOMIB) system based on two sets of generators.
    A COOMIB considers a constant deviation of the rotor angle of each generator compared to the Partial
    Center Of Angle (PCOA) of each cluster.
    """

    def __init__(self, network: Network, critical_cluster: GeneratorCluster, non_critical_cluster: GeneratorCluster):
        """
        Initialize the OMIB model.

        :param network: Network for which the OMIB must be built.
        :param critical_cluster: Cluster of generators in the power system considered as critical.
        :param non_critical_cluster: Cluster of generators in the power system considered as non critical.
        """
        for generator in critical_cluster.generators.union(non_critical_cluster.generators):
            # Reset generators as no OMIB update is required
            generator.reset()

        # Structure for intermediate results to improve performances
        self._angular_deviations: DefaultDict[str, Dict[float, float]] = defaultdict(dict)

        super().__init__(network=network, critical_cluster=critical_cluster, non_critical_cluster=non_critical_cluster)

    def _get_generator_angular_deviation(
        self, generator_name: str, generator_cluster: GeneratorCluster, time: float, state: NetworkState
    ) -> float:
        """
        Get the angular deviation of a generator compared to the partial center of angle of its cluster at a specified
        time.

        :param generator_name: Name of the generator to consider. It must belong to the cluster.
        :param generator_cluster: Cluster containing the generator.
        :param time: Time (s) at which the generator rotor angles must be considered.
        :param state: State of the network when the angular deviation must be computed.
        :return: The angular deviation (rad).
        :raise GeneratorClusterMemberException if the generator is not in the cluster.
        """
        if not generator_cluster.contains_generator(generator_name):
            # Generator not in the cluster
            raise GeneratorClusterMemberException(generator_cluster, generator_name)
        # Offset is constant and always computed based on the angles at t = 0
        time = 0
        try:
            return self._angular_deviations[generator_name][time]
        except KeyError:
            # Compute deviation (always considering angles at time t = 0)
            deviation = generator_cluster.get_generator_angular_deviation(generator_name, time, NetworkState.PRE_FAULT)
            self._angular_deviations[generator_name][time] = deviation
            return deviation
