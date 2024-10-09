# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from .omib import OMIB
from deeac.domain.models import Network, NetworkState
from deeac.domain.models import GeneratorCluster


class RevisedOMIB(OMIB):
    """
    Class modeling a revised OMIB system based on two sets of generators.
    A revised OMIB is similar to an OMIB, except that the initial angle is computed based on the partial angles of
    both the critical and non-critical sets.
    """

    def __init__(self, network: Network, critical_cluster: GeneratorCluster, non_critical_cluster: GeneratorCluster):
        """
        Initialize the OMIB model.

        :param network: Network for which the OMIB must be built.
        :param critical_cluster: Cluster of generators in the power system considered as critical.
        :param non_critical_cluster: Cluster of generators in the power system considered as non critical.
        """
        # Revised initial angle
        state = NetworkState.PRE_FAULT
        self._revised_initial_angle = (
            critical_cluster.get_partial_center_of_angle(0, state) -
            non_critical_cluster.get_partial_center_of_angle(0, state)
        )
        super().__init__(network=network, critical_cluster=critical_cluster, non_critical_cluster=non_critical_cluster)

    @property
    def initial_rotor_angle(self) -> float:
        """
        Return the initial rotor angle.

        return: The initial rotor angle of this OMIB system.
        :raise: OMIBRotorAngleException if the angle cannot be computed.
        """
        return self._revised_initial_angle
