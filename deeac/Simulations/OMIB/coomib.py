"""
Module for coomib.

:module: coomib
"""
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

from deeac.Models.generator_cluster import GeneratorCluster
from deeac.Models.network import Network, NetworkState, NetworkComputed
from deeac.Simulations.OMIB.omib import OMIB


class COOMIB(OMIB):
    """
    Coomib.
    
    Rationale:
        This class implements EEAC simulation logic (OMIB, EAC, or trajectory
        math) that runs during the evaluation stage. It consumes model objects
        and produces stability-relevant quantities for the final selection step.
    
    :ivar network: network.
    :ivar critical_cluster: critical cluster.
    :ivar non_critical_cluster: non critical cluster.
    """

    def __init__(self, network: Network,

                 computed: NetworkComputed,
                 critical_cluster: GeneratorCluster,
                 non_critical_cluster: GeneratorCluster):
        """
        Initialize the OMIB model.
        
        :param network: Network for which the OMIB must be built.
        :param critical_cluster: Cluster of generators in the power system considered as critical.
        :param non_critical_cluster: Cluster of generators in the power system considered as non critical.
        """
        # Generators do not carry trajectory state in the simplified pipeline.

        # Structure for intermediate results to improve performances
        self._angular_deviations: DefaultDict[str, Dict[float, float]] = defaultdict(dict)

        super().__init__(network=network,
                         computed=computed,
                         critical_cluster=critical_cluster,
                         non_critical_cluster=non_critical_cluster)

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
        """
        if not generator_cluster.contains_generator(generator_name):
            # Generator not in the cluster
            raise KeyError(generator_cluster, generator_name)
        # Offset is constant and always computed based on the angles at t = 0
        time = 0
        try:
            return self._angular_deviations[generator_name][time]
        except KeyError:
            # Compute deviation (always considering angles at time t = 0)
            deviation = generator_cluster.get_generator_angular_deviation(generator_name, time, NetworkState.PRE_FAULT)
            self._angular_deviations[generator_name][time] = deviation
            return deviation
