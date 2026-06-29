"""
Module for selector.

:module: selector
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

from deeac.Models.generator_cluster import GeneratorCluster
from deeac.Models.generator import Generator
from deeac.enums import OMIBStabilityState, OMIBSwingState


class CriticalClusterResults:
    """
    CriticalClusterResults.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar critical_cluster: critical cluster.
    :ivar non_critical_cluster: non critical cluster.
    :ivar critical_angle: critical angle.
    :ivar critical_time: critical time.
    :ivar maximum_angle: maximum angle.
    :ivar maximum_time: maximum time.
    :ivar generators: generators.
    :ivar omib_stability_state: omib stability state.
    :ivar omib_swing_state: omib swing state.
    """
    __slots__ = (
        "critical_cluster",
        "non_critical_cluster",
        "critical_angle",
        "critical_time",
        "maximum_angle",
        "maximum_time",
        "generators",
        "omib_stability_state",
        "omib_swing_state",
    )

    def __init__(
        self,
        critical_cluster: GeneratorCluster,
        non_critical_cluster: GeneratorCluster,
        critical_angle: float,
        critical_time: float,
        maximum_angle: float,
        maximum_time: float,
        generators: List[Generator],
        omib_stability_state: OMIBStabilityState,
        omib_swing_state: OMIBSwingState,
    ) -> None:
        """
        Initialize the object.
        
        :param critical_cluster: critical cluster.
        :param non_critical_cluster: non critical cluster.
        :param critical_angle: critical angle.
        :param critical_time: critical time.
        :param maximum_angle: maximum angle.
        :param maximum_time: maximum time.
        :param generators: generators.
        :param omib_stability_state: omib stability state.
        :param omib_swing_state: omib swing state.
        """
        self.critical_cluster = critical_cluster
        self.non_critical_cluster = non_critical_cluster
        self.critical_angle = critical_angle
        self.critical_time = critical_time
        self.maximum_angle = maximum_angle
        self.maximum_time = maximum_time
        self.generators = generators
        self.omib_stability_state = omib_stability_state
        self.omib_swing_state = omib_swing_state
