"""
Module for generator_cluster.

:module: generator_cluster
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Dict, List

import numpy as np

from deeac.Models.generator import Generator
from deeac.Models.generator_snapshot import GeneratorSnapshot
from deeac.Models.network import NetworkState


class GeneratorCluster:
    """
    Generatorcluster.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar generator_snapshot: generator snapshot (time-0 angles/parameters).
    :ivar generator_indices: indices of generators belonging to this cluster.
    
    The cluster represents one side of the CC/NC split used to build an OMIB equivalent.
    Partial center of angle uses inertia-weighted averages as in the EEAC paper.
    """

    def __init__(self, generator_snapshot: GeneratorSnapshot, generator_indices: List[int]):
        """
        Initialize the cluster
        
        :param generator_snapshot: Generator snapshot for this cluster.
        :param generator_indices: Generator indices in this cluster.
        :raise PartialCenterOfAngleException if the total inertia off the cluster is 0.
        """
        if not generator_indices:
            # Cluster cannot be empty
            raise ValueError()

        self._generator_snapshot = generator_snapshot
        self._generator_indices = list(generator_indices)
        self._generators = {generator_snapshot.generators[i].name: i for i in self._generator_indices}

        # Compute characteristics of this cluster
        self._total_inertia = float(np.sum(generator_snapshot.inertia_coefficients[self._generator_indices]))
        self._total_mechanical_power = float(np.sum(generator_snapshot.mechanical_powers[self._generator_indices]))
        self._partial_center_of_angles: Dict[float, float] = {
            0: float(
                np.sum(
                    generator_snapshot.inertia_coefficients[self._generator_indices]
                    * generator_snapshot.rotor_angles[self._generator_indices]
                )
            ) / self._total_inertia
        }

        # Initialize network state for performance purposes
        self._pre_state = NetworkState.PRE_FAULT

    def __repr__(self):
        """
        repr  .
        
        :return: Return value.
        """
        generators = ")(".join([repr(self._generator_snapshot.generators[i]) for i in self._generator_indices])
        return (
            f"Cluster of generators: Dynamic generators=[({generators})]"
        )

    @property
    def generators(self) -> List[Generator]:
        """
        Get the set of generators in this cluster.
        
        :return: The set of generators in the cluster.
        """
        return [self._generator_snapshot.generators[i] for i in self._generator_indices]

    @property
    def total_inertia(self) -> float:
        """
        Total inertia.
        
        :return: Return value.
        :rtype: float
        """
        return self._total_inertia

    @property
    def total_mechanical_power(self) -> float:
        """
        Total mechanical power.
        
        :return: Return value.
        :rtype: float
        """
        return self._total_mechanical_power

    def contains_generator(self, generator_name: str) -> bool:
        """
        Determine if a generator is in the cluster.
        
        :param generator_name: Name of the generator.
        :return: True if the generator is in the cluster, False otherwise.
        """
        return generator_name in self._generators

    def get_partial_center_of_angle(self, time: float, state: NetworkState):
        """
        Get the partial center of angle at a specific time.
        
        :param time: Time (s) for which the center of angle must be computed.
        :param state: Network state in which the network should be when computing the center of angle.
        :return: The partial center of angle at the specific time (rad).
        """
        try:
            return self._partial_center_of_angles[time]
        except KeyError:
            # Angle not computed yet
            if time == 0:
                # Initial angle is always associated to the PRE-FAULT state
                state = self._pre_state
            self._partial_center_of_angles[time] = 0
            if time != 0:
                # Rotor angles are stored as a single snapshot for time 0 in the simplified pipeline.
                time = 0
            self._partial_center_of_angles[time] = self._partial_center_of_angles[0]
        return self._partial_center_of_angles[time]

    def get_generator_angular_deviation(self, generator_name: str, time: float, state: NetworkState) -> float:
        """
        Compute the rotor angular deviation of a generator in the cluster compared to the partial center of angle.
        
        :param generator_name: Name of the generator for which the angular deviation must be computed.
        :param time: Time (s) at which the deviation must be computed. Time t=0 corresponds to initial rotor angles.
        :param state: Network state in which the network should be when computing the angular deviation.
        :return: The angular deviation.
        """
        try:
            generator_index = self._generators[generator_name]
        except KeyError:
            # Generator not in cluster.
            raise KeyError(self, generator_name)
        if time != 0:
            time = 0
        if time == 0:
            state = self._pre_state
        angular_deviation = (
                self._generator_snapshot.rotor_angles[generator_index]
                - self.get_partial_center_of_angle(time, state)
        )
        return angular_deviation
