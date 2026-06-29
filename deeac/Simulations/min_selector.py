"""
Module for min_selector.

:module: min_selector
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List

import numpy as np

from deeac.Simulations.selector import CriticalClusterResults


def select_min_critical_cluster(cluster_results: List[CriticalClusterResults]) -> int:
    """
    Select one of the critical clusters based on their results.
    
    :param cluster_results: List of cluster results.
    :return: The index of the cluster in the input list.
    """
    if cluster_results is None or len(cluster_results) == 0:
        # No element to compare
        raise ValueError()
    times = np.array([result.critical_time for result in cluster_results], dtype=float)
    return int(times.argmin())
