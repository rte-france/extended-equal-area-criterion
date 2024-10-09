# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from pydantic import BaseModel
from abc import ABC, abstractmethod
from typing import List

from deeac.domain.models import GeneratorCluster


class CriticalClusterResults(BaseModel):
    """
    Results related to a critical cluster.
    """
    critical_cluster: GeneratorCluster
    non_critical_cluster: GeneratorCluster
    critical_angle: float
    critical_time: float
    maximum_angle: float
    maximum_time: float

    class Config:
        arbitrary_types_allowed = True


class CriticalClusterSelector(ABC):
    """
    Selector of critical clusters of generators.
    """

    @classmethod
    @abstractmethod
    def select_cluster(cls, cluster_results: List[CriticalClusterResults]) -> int:
        """
        Select one of the critical clusters based on their results.

        :param cluster_results: List of cluster results.
        :return: The index of the cluster in the input list.
        """
        pass
