# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List

from .selector import CriticalClusterSelector, CriticalClusterResults
from deeac.domain.exceptions import CriticalClusterSelectorException


class MinCriticalClusterSelector(CriticalClusterSelector):
    """
    Selector of critical clusters of generators, based on the minimum critical clearing time.
    """

    @classmethod
    def select_cluster(cls, cluster_results: List[CriticalClusterResults]) -> int:
        """
        Select one of the critical clusters based on their results.

        :param cluster_results: List of cluster results.
        :return: The index of the cluster in the input list.
        """
        if cluster_results is None or len(cluster_results) == 0:
            # No element to compare
            raise CriticalClusterSelectorException()
        return cluster_results.index(min(cluster_results, key=lambda r: r.critical_time))
