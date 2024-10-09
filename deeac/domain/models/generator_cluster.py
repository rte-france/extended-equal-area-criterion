# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Set, Dict

from .generator import DynamicGenerator
from .network import NetworkState
from deeac.domain.exceptions import (
    PartialCenterOfAngleException, GeneratorClusterMemberException, EmptyGeneratorClusterException
)


class GeneratorCluster:
    """
    Cluster of generators in a power system.
    """

    def __init__(self, dynamic_generators: Set[DynamicGenerator]):
        """
        Initialize the cluster

        :param dynamic_generators: List of dynamic generators in this cluster.
        :raise PartialCenterOfAngleException if the total inertia off the cluster is 0.
        """
        if not dynamic_generators:
            # Cluster cannot be empty
            raise EmptyGeneratorClusterException()

        self._dynamic_generators = dynamic_generators

        # Map generators to their names to improve performances
        self._generators = {gen.name: gen for gen in dynamic_generators}

        # Compute characteristics of this cluster
        self._total_inertia = 0
        self._total_mechanical_power = 0
        self._partial_center_of_angles: Dict[float, float] = {0: 0}
        for generator in dynamic_generators:
            self._total_inertia += generator.inertia_coefficient
            self._total_mechanical_power += generator.mechanical_power
            self._partial_center_of_angles[0] += generator.inertia_coefficient * generator.get_rotor_angle(0)
        try:
            self._partial_center_of_angles[0] /= self._total_inertia
        except ZeroDivisionError:
            raise PartialCenterOfAngleException(self)

        # Initialize network state for performance purposes
        self._pre_state = NetworkState.PRE_FAULT

    def __repr__(self):
        """
        Representation of a generator cluster.
        """
        generators = ")(".join([repr(generator) for generator in self._dynamic_generators])
        return (
            f"Cluster of generators: Dynamic generators=[({generators})]"
        )

    @property
    def generators(self) -> Set[DynamicGenerator]:
        """
        Get the set of generators in this cluster.

        :return: The set of generators in the cluster.
        """
        return self._dynamic_generators

    @property
    def total_inertia(self) -> float:
        """
        Get the total inertia of the cluster.

        return: The total inertia of the cluster.
        """
        return self._total_inertia

    @property
    def total_mechanical_power(self) -> float:
        """
        Get the total mechanical power of the cluster.

        return: The total mechanical power.
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
            for generator in self._dynamic_generators:
                self._partial_center_of_angles[time] += generator.inertia_coefficient * generator.get_rotor_angle(time)
                # Check that generator rotor angle was computed in the right network state
                assert generator.get_network_state(time) == state
            self._partial_center_of_angles[time] /= self._total_inertia
        return self._partial_center_of_angles[time]

    def get_generator_angular_deviation(self, generator_name: str, time: float, state: NetworkState) -> float:
        """
        Compute the rotor angular deviation of a generator in the cluster compared to the partial center of angle.

        :param generator_name: Name of the generator for which the angular deviation must be computed.
        :param time: Time (s) at which the deviation must be computed. Time t=0 corresponds to initial rotor angles.
        :param state: Network state in which the network should be when computing the angular deviation.
        :return: The angular deviation.
        :raise GeneratorClusterMemberException if the generator is not in the cluster.
        """
        try:
            generator = self._generators[generator_name]
        except KeyError:
            # Generator not in cluster.
            raise GeneratorClusterMemberException(self, generator_name)
        if time == 0:
            # Initial angle is always associated to the PRE-FAULT state
            state = self._pre_state
        # Check that generator rotor angle was computed in the right network state
        angular_deviation = generator.get_rotor_angle(time) - self.get_partial_center_of_angle(time, state)
        assert generator.get_network_state(time) == state
        return angular_deviation
