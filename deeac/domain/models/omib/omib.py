# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from functools import lru_cache

import numpy as np
import math
import bisect
from enum import Enum
from collections import defaultdict
from abc import ABC, abstractmethod
from typing import Dict, Tuple, List

from deeac.domain.models import GeneratorCluster, NetworkState, Network
from deeac.domain.exceptions import OMIBInertiaException, OMIBException, OMIBAngleShiftException


class OMIBSwingState(Enum):
    """
    Swing state of the OMIB
    """
    BACKWARD = "BACKWARD"
    FORWARD = "FORWARD"


class OMIBStabilityState(Enum):
    """
    Stability state of the OMIB
    """
    ALWAYS_STABLE = "ALWAYS STABLE"
    ALWAYS_UNSTABLE = "ALWAYS UNSTABLE"
    POTENTIALLY_STABLE = "POTENTIALLY STABLE"
    UNKNOWN = "UNKNOWN"


class OMIB(ABC):
    """
    Class modeling a One Machine Infinite Bus system based on two sets of generators (critical and non-critical).
    """

    def __init__(self, network: Network, critical_cluster: GeneratorCluster, non_critical_cluster: GeneratorCluster):
        """
        Initialize the OMIB model.

        :param network: Network for which the OMIB must be built.
        :param critical_cluster: Cluster of generators in the power system considered as critical.
        :param non_critical_cluster: Cluster of generators in the power system considered as non-critical.
        :raise: OMIBEmptyCriticalClusterException if the critical cluster is empty.
        """

        self._network = network
        self._critical_cluster = critical_cluster
        self._non_critical_cluster = non_critical_cluster

        # Initialize states for performances
        self._pre_state = NetworkState.PRE_FAULT
        self._during_state = NetworkState.DURING_FAULT
        self._post_state = NetworkState.POST_FAULT

        # Initialize states (swing state is forward by default)
        self._swing_state = OMIBSwingState.FORWARD
        self._swing_factor = 1
        self._stability_state = OMIBStabilityState.UNKNOWN

        # Compute inertia
        self.total_inertia = non_critical_cluster.total_inertia + critical_cluster.total_inertia
        try:
            self.inertia = (non_critical_cluster.total_inertia * critical_cluster.total_inertia) / self.total_inertia
        except ZeroDivisionError:
            raise OMIBInertiaException(self)

        # Maximum and constant electric powers, and angle shifts for each couple (state, time) where time is the time
        # at which the generator rotor angles must be considered.
        self._maximum_electric_powers: Dict[Tuple[NetworkState, float], float] = dict()
        self._constant_electric_powers: Dict[Tuple[NetworkState, float], float] = dict()
        self._angle_shifts: Dict[Tuple[NetworkState, float], float] = dict()

        # Mechanical power
        self._mechanical_power = None

        # Initial angle
        self._initial_rotor_angle = None

        # Build initial state when network is in pre-fault state (allows to compute the initial angle)
        self._update_angles = [(None, 0, self._pre_state)]
        self._build_state(state=self._pre_state)

        # Build initial during and post-fault states
        self._update_angles = [
            (self.initial_rotor_angle, 0, self._during_state),
            (self.initial_rotor_angle, 0, self._post_state)
        ]
        for state in [self._during_state, self._post_state]:
            self._build_state(state=state)

        # Check if back-swing instability
        electric_power = self.get_electric_power(self.initial_rotor_angle, self._during_state)
        if self.mechanical_power < electric_power:
            self._swing_state = OMIBSwingState.BACKWARD
            self._swing_factor = -1

        # Compute update angles (angle, time, network state)
        self._compute_update_angles()

        # Build remaining OMIB states
        for state in [self._during_state, self._post_state]:
            self._build_state(state=state, compute_at_initial_time=False)

    def __repr__(self):
        """
        Representation of an OMIB.
        """
        properties = defaultdict(list)
        for angle, time, state in sorted(self._update_angles, key=lambda up_angle: self._swing_factor * up_angle[0]):
            shift, const_power, max_power = self.get_properties(state, angle)
            properties[state].append(
                f"\t\t\tAngle: {round(angle, 3)} rad [{round(np.rad2deg(angle), 3)} deg] - "
                f"Time: {round(time * 1000, 3)} ms - "
                f"Angle shift: {round(shift, 3)} rad [{round(np.rad2deg(shift), 3)} deg] - "
                f"Constant power: {round(const_power, 3)} p.u. - "
                f"Maximum power: {round(max_power, 3)} p.u."
            )

        critical_generators = ", ".join(sorted([gen.name for gen in self.critical_cluster.generators]))
        separator = "\n"
        return (
            f"OMIB:\n"
            f"\tType: {type(self).__name__}\n"
            f"\tStability state: {self.stability_state.value}\n"
            f"\tSwing state: {self.swing_state.value}\n"
            f"\tCritical generators: {critical_generators}\n"
            f"\tProperties:\n"
            f"\t\tPRE-FAULT:\n"
            f"{separator.join(properties[self._pre_state])}"
            f"\n\t\tDURING-FAULT:\n"
            f"{separator.join(properties[self._during_state])}"
            f"\n\t\tPOST-FAULT:\n"
            f"{separator.join(properties[self._post_state])}"
        )

    @property
    def network(self) -> Network:
        """
        Network on which the OMIB is applied.

        :return: The network associated to this OMIB.
        """
        return self._network

    @property
    def critical_cluster(self) -> GeneratorCluster:
        """
        Get the critical cluster associated to this OMIB.

        :return: The critical cluster.
        """
        return self._critical_cluster

    @property
    def non_critical_cluster(self) -> GeneratorCluster:
        """
        Get the non-critical cluster associated to this OMIB.

        :return: The non-critical cluster.
        """
        return self._non_critical_cluster

    @property
    def swing_state(self) -> OMIBSwingState:
        """
        Return the swing state of this OMIB.

        :return: The swing state.
        """
        return self._swing_state

    @property
    def stability_state(self) -> OMIBStabilityState:
        """
        Return the stability state of this OMIB.

        :return: The stability state.
        """
        return self._stability_state

    @stability_state.setter
    def stability_state(self, state: OMIBStabilityState):
        """
        Change the stability state.

        :param state: The stability state to set.
        """
        self._stability_state = state

    def _compute_update_angles(self):
        """
        Compute the OMIB angles at the time instants when the generator angles were updated.
        All the generators are assumed to have been updated at the same time instants.
        """
        # Initial angles
        self._update_angles = [
            (self.initial_rotor_angle, 0, self._pre_state),
            (self.initial_rotor_angle, 0, self._during_state),
            (self.initial_rotor_angle, 0, self._post_state)
        ]

        # Get observation times at which the generator rotor angles are known
        generators = self._critical_cluster.generators.union(self._non_critical_cluster.generators)
        generator = next(generator for generator in generators)
        observation_times = generator.observation_times

        # Compute OMIB angles so that they monotonously increase
        previous_angle = self.initial_rotor_angle
        for time in observation_times[1:]:
            network_state = generator.get_network_state(time)
            angle = self._get_rotor_angle_at_time(time, network_state)
            if angle * self._swing_factor < previous_angle * self._swing_factor:
                # Do not consider decreasing angles
                continue
            self._update_angles.append((angle, time, network_state))
            previous_angle = angle

    def get_cluster_data(
        self, cluster: GeneratorCluster, update_time: float, state: NetworkState
    ) -> List[Tuple[str, str, float]]:
        """
        Fetches the name, bus name and angular deviation of every generator of a given cluster
        :param cluster: group of generators
        :param update_time: observation times
        :param state: State that must be built.
        :return: the list of name, bus name and angular deviation of every generator found in the cluster
        """
        data_list = list()
        for generator in cluster.generators:
            name = generator.name
            angular_deviation = self._get_generator_angular_deviation(
                        generator_name=name,
                        generator_cluster=cluster,
                        time=update_time,
                        state=state
                    )
            data_list.append((name, generator.bus.name, angular_deviation))
        return data_list

    def _build_state(self, state: NetworkState, compute_at_initial_time: bool = True):
        """
        Build the specific OMIB state, computing the constant and maximum electric powers, and the angle shift.

        :param state: State that must be built.
        :param compute_at_initial_time: True if the state must also be built for the initial time
        """
        # Extract REN cluster
        simplified_network = self._network.get_state(state)
        ren_cluster = {b for a in simplified_network.admittance_matrix.ren_buses for b in a.ren}

        # Cluster combinations
        if not(ren_cluster):
            cluster_combinations = [
                (self._critical_cluster, self._non_critical_cluster),
                (self._critical_cluster, self._critical_cluster),
                (self._non_critical_cluster, self._non_critical_cluster)
            ]
        else:
            cluster_combinations = [
                (self._critical_cluster, self._non_critical_cluster),
                (self._critical_cluster, self._critical_cluster),
                (self._non_critical_cluster, self._non_critical_cluster),
                (self._critical_cluster, ren_cluster),
                (self._non_critical_cluster, ren_cluster)
            ]

        # Inertia ratios
        try:
            non_critical_inertia_ratio = self._non_critical_cluster.total_inertia / self.total_inertia
            critical_inertia_ratio = self._critical_cluster.total_inertia / self.total_inertia
            inertia_ratio_difference = non_critical_inertia_ratio - critical_inertia_ratio
        except ZeroDivisionError:
            raise OMIBInertiaException(self)

        # Admittance matrix according to the state
        admittance_matrix = simplified_network.admittance_matrix.reduction

        # Update times according to the state
        if compute_at_initial_time:
            update_times = [time for _, time, network_state in self._update_angles if network_state == state]
        else:
            update_times = [time for _, time, network_state in self._update_angles if network_state == state if time > 0]

        for update_time in update_times:
            # Structures to store results
            constant_power_terms = [0, 0, 0]
            first_constant_terms = [0, 0, 0]
            second_constant_terms = [0, 0, 0]

            # Conductance and susceptance products for the cluster combinations
            for combination in cluster_combinations:
                (cluster1, cluster2) = combination
                term_pos = 0 if combination == cluster_combinations[1] else 1
                # Gather all data at once before looping over them
                data_cluster1 = self.get_cluster_data(cluster1, update_time, state)

                if cluster1 == cluster2:
                    # Critical / critical or non-critical / non-critical
                    data_cluster2 = data_cluster1
                else:
                    if cluster2 != ren_cluster:
                        # Critical / non-critical
                        data_cluster2 = self.get_cluster_data(cluster2, update_time, state)
                    else:
                        # Critical / REN or non-critical / REN
                        data_cluster2 = [(l.name, l.bus.name, math.atan2(l.reactive_power, l.active_power))
                                         for l in ren_cluster]
                        #data_cluster2 = [(l.name, l.bus.name, 0) for l in ren_cluster]

                # Using arrays
                gen1_names, gen1_buses, gen1_angles = map(np.array, zip(*data_cluster1))
                gen2_names, gen2_buses, gen2_angles = map(np.array, zip(*data_cluster2))

                # Angular differences
                delta_theta = gen1_angles[:, None] - gen2_angles[None, :]
                sine, cosine = np.sin(delta_theta), np.cos(delta_theta)

                # Module products
                if cluster2 != ren_cluster:
                    get_volt = np.vectorize(self._network.get_generator_voltage_amplitude_product)
                    A = get_volt(gen1_names[:, None], gen2_names[None, :])
                else:
                    v1 = np.array(
                        [abs(a.generator.internal_voltage) for a in cluster1.generators if a.name in gen1_names])
                    #i2 = np.array([abs(a.bus.voltage) for a in cluster2 if a.name in gen2_names])
                    i2 = np.array([abs(a.current) for a in cluster2 if a.name in gen2_names])
                    A = v1[:, None] * i2[None, :]

                # Admittance sub-matrix
                Y = np.array([[admittance_matrix[b1, b2] for b2 in gen2_buses] for b1 in gen1_buses])
                G, B = Y.real, Y.imag

                # Sum calculation
                if cluster2 != ren_cluster:
                    if cluster1 == cluster2:
                        constant_power_terms[term_pos] += np.sum(cosine * A * G + sine * A * B)
                    else:
                        first_constant_terms[0] += np.sum(sine * A * B)
                        first_constant_terms[1] += np.sum(cosine * A * G)
                        second_constant_terms[0] += np.sum(cosine * A * B)
                        second_constant_terms[1] += np.sum(sine * A * G)
                else:
                    if combination == cluster_combinations[4]:
                        constant_power_terms[2] += np.sum(cosine * A * G + sine * A * B)
                    else:
                        first_constant_terms[2] += np.sum(cosine * A * G + sine * A * B)
                        second_constant_terms[2] += np.sum(cosine * A * B - sine * A * G)

            # First and second constants in maximum electric power and angle shift
            first_constant = (first_constant_terms[0] + first_constant_terms[1] * inertia_ratio_difference
                             + first_constant_terms[2] * non_critical_inertia_ratio)
            second_constant = (second_constant_terms[0] - second_constant_terms[1] * inertia_ratio_difference
                             + second_constant_terms[2] * non_critical_inertia_ratio)

            # Maximum electric power
            self._maximum_electric_powers[(state, update_time)] = np.sqrt(first_constant ** 2 + second_constant ** 2)

            # Angle shift
            try:
                self._angle_shifts[(state, update_time)] = - math.atan2(first_constant, second_constant)
            except ZeroDivisionError:
                raise OMIBAngleShiftException(self)

            # Constant electric power
            self._constant_electric_powers[(state, update_time)] = (
                non_critical_inertia_ratio * constant_power_terms[0]
                - critical_inertia_ratio * (constant_power_terms[1] + constant_power_terms[2])
            )

    @abstractmethod
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
        :raise: GeneratorClusterMemberException if the generator is not in the cluster.
        """
        pass

    @lru_cache(maxsize=None)
    def _get_update_angle(self, rotor_angle: float, state: NetworkState) -> Tuple[float, float, NetworkState]:
        """
        Get the update angle associated to a specified angle and OMIB state.
        The initial rotor angle is not considered in the post-fault state if other update points exist.
        In this case, any angle before the first post-fault update will be associated to this first update point.

        :param rotor_angle: The rotor angle to consider (rad).
        :param state: The network state to consider for the OMIB curve.
        :return: The update angle as a tuple containing the rotor angle itself, and the corresponding time and network
                 state.
        """
        update_angles = [angle for angle in self._update_angles if angle[2] == state]
        if state == self._post_state and len(update_angles) != 1:
            # Do not consider update at initial angle for the post-fault state
            update_angles = update_angles[1:]

        # Remember an element of self._update_angles looks like (angle, time, network_state)
        angles_only = [self._swing_factor * angle[0] for angle in update_angles]
        target = self._swing_factor * rotor_angle

        index = bisect.bisect_right(angles_only, target)

        if index == len(update_angles):
            return update_angles[-1]
        return update_angles[index - 1] if index > 0 else update_angles[0]

    @property
    def mechanical_power(self) -> float:
        """
        Return the mechanical power of the machine.

        :return: The mechanical power of the OMIB system.
        """
        if self._mechanical_power is None:
            self._mechanical_power = (
                self._non_critical_cluster.total_inertia * self._critical_cluster.total_mechanical_power -
                self._critical_cluster.total_inertia * self._non_critical_cluster.total_mechanical_power
            ) / self.total_inertia
        return self._mechanical_power

    @property
    def initial_rotor_angle(self) -> float:
        """
        Return the initial rotor angle of this OMIB, at the intersection of the mechanical power and the
        pre-state electric power.

        return: The initial rotor angle of this OMIB system.
        :raise: OMIBException if the angle cannot be computed.
        """
        if self._initial_rotor_angle is not None:
            return self._initial_rotor_angle

        # Get OMIB properties
        angle_shift, constant_electric_power, maximum_electric_power = self.get_properties(self._pre_state)
        try:
            arcsin_arg = ((self.mechanical_power - constant_electric_power) / maximum_electric_power)
        except ZeroDivisionError:
            raise OMIBException(
                self,
                "Cannot compute initial rotor angle as maximum electric power is equal to 0 in PRE-FAULT state."
            )
        if arcsin_arg < -1 or arcsin_arg > 1:
            raise OMIBException(
                self,
                "Cannot compute initial rotor angle as arcsin argument is not between -1 and 1."
            )
        self._initial_rotor_angle = angle_shift + np.arcsin(arcsin_arg)
        return self._initial_rotor_angle

    @property
    def update_angles(self) -> List[Tuple[float, float, NetworkState]]:
        """
        Return the different update angles at which the OMIB was updated.

        :return: A list of the update angles associated to their time and network state.
        """
        return self._update_angles

    def get_electric_power(
        self, rotor_angle: float, state: NetworkState, use_initial_angle_curves: bool = False
    ) -> float:
        """
        Get the OMIB electric power corresponding to a machine rotor angle in a specific network state using the
        generator rotor angles at the specified time.
        If use_initial_angle_curves is False, the initial rotor angle is not considered in the post-fault state.
        Any angle before the first post-fault update will be associated to the OMIB curve obtained with this first
        update point.

        :param rotor_angle: Rotor angle for which the power must be computed.
        :param state: State of the network for which the power must be computed.
        :param use_initial_angle_curves: If True, the electric power is obtained from the curve derived from the initial
                                         rotor angle value. Otherwise, use the closest rotor angle update, smaller than
                                         the requested angle.
        :return: The electric power.
        """
        if use_initial_angle_curves:
            # Use initial curve
            angle_shift, constant_electric_power, maximum_electric_power = self.get_properties(state)
        else:
            # Get OMIB properties at specified angle
            angle_shift, constant_electric_power, maximum_electric_power = self.get_properties(state, rotor_angle)
        return constant_electric_power + maximum_electric_power * np.sin(rotor_angle - angle_shift)

    @lru_cache(maxsize=None)
    def get_properties(self, state: NetworkState, rotor_angle: float = None) -> Tuple[float, float, float]:
        """
        Get the properties of this OMIB in the specified state and at the specified angle.
        The three properties are respectively:
            - angle shift
            - constant electric power
            - maximum electric power
        If rotor_angle is specified with the post-fault state, the initial rotor angle is not considered,
        except if rotor_angle is the initial angle.
        Any angle before the first post-fault update will be associated to the OMIB curve obtained with this first
        update point, except if this angle is the initial angle.

        :param state: State of the network for which the properties must be returned.
        :param rotor_angle: Angle (rad) at which the properties must be computed. If not specified,
                            use the initial OMIB angle.
        :return: The tuple (angle shift, constant electric power, maximum electric power)
        """
        # Get update time corresponding to the specified angle a state
        if rotor_angle is None or math.isclose(rotor_angle, self.initial_rotor_angle, abs_tol=10e-9):
            # Return properties computed at initial time
            update_time = 0
        else:
            _, update_time, _ = self._get_update_angle(rotor_angle, state)
        point = (state, update_time)
        return (
            self._angle_shifts[point],
            self._constant_electric_powers[point],
            self._maximum_electric_powers[point]
        )

    def _get_rotor_angle_at_time(self, time: float, state: NetworkState) -> float:
        """
        Compute the rotor angle of the OMIB at a specific time. The time reference (t = 0) is considered as the time
        corresponding to the initial rotor angle.
        This angle is estimated as the difference between the partial centers of angles of the critical and non-critical
        generator clusters. It implies that the rotor angles of all the generators must be known at this specific time.

        :param time: Time (s) to which the angle must correspond.
        :param state: Network state to consider for the rotor angle trajectory.
        :return: The angle (rad) corresponding the specified time.
        """
        critical_pcoa = self._critical_cluster.get_partial_center_of_angle(time, state)
        non_critical_pcoa = self._non_critical_cluster.get_partial_center_of_angle(time, state)
        return critical_pcoa - non_critical_pcoa
