# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import numpy as np
import cmath
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Set, List
from pydantic import BaseModel
import matplotlib.pyplot as plt
from matplotlib import rc

from deeac.domain.models import Network, NetworkState, DynamicGenerator
from deeac.domain.exceptions import GeneratorTrajectoryUpdateTimeException


class GeneratorTrajectoryTime(BaseModel):
    """
    Representation of a time point on the generator rotor angle trajectory.

    :param network_state: Network state considered starting from this point (i.e. in the future).
    :param time: Time (s) corresponding to the point on the trajectory.
    """
    network_state: NetworkState
    time: float


class GeneratorRotorAnglesTrajectoryCalculator(ABC):
    """
    Series in charge of finding the generator angles at a specific time along the rotor angle trajectories.
    """

    def __init__(self, network: Network, transition_time_shift: float = 0):
        """
        Initialize the series with the network containing the generators.

        :param network: Network to use with this series.
        :param transition_time_shift: Positive shift (s) to apply to the transition time. It is only unsed to compute
                                      the rotor angles after the transition time, allowing to obtain improved curves in
                                      further analyses. The angle outputted for the transition time is not altered by
                                      this shift.
        """
        self._network = network
        self._transition_time_shift = transition_time_shift
        self._shifted_transition_time = None

        # Initialize containers for intermediate results to improve performances
        self._generator_electric_powers = defaultdict(lambda: defaultdict(dict))
        self._neg_generator_electric_power_derivatives = defaultdict(lambda: defaultdict(dict))

        # Initialize network state for performance purposes
        self._pre_state = NetworkState.PRE_FAULT
        self._during_state = NetworkState.DURING_FAULT
        self._post_state = NetworkState.POST_FAULT

    def _compute_generator_electric_power(
        self, generator: DynamicGenerator, generators: List[DynamicGenerator], trajectory_time: GeneratorTrajectoryTime,
        compute_first_derivative: bool = False
    ):
        """
        Compute the electric power of a generator and its derivative, if needed.

        :param generator: The generator for which the electric power must be computed.
        :param generators: List of all the generators in the network.
        :param trajectory_time: Trajectory time to consider when computing the electric power.
        :param compute_first_derivative: True if the first derivative of the electric power must also be computed.
        :return: The generator electric power.
        """
        # Get time and network state
        time = trajectory_time.time
        state = trajectory_time.network_state

        electric_power = 0
        neg_electric_power_derivative = 0
        generator_angle = generator.get_rotor_angle(time)
        for other_generator in generators:
            # Get product of internal voltages
            voltage_product = self._network.get_generator_voltage_amplitude_product(
                generator.name,
                other_generator.name
            )
            # Compute admittance amplitude
            admittance_amplitude, admittance_angle = self._network.get_admittance(
                generator.bus.name,
                other_generator.bus.name,
                state
            )
            voltage_admittance = voltage_product * admittance_amplitude

            # Get other generator angle at evaluation point
            other_generator_angle = other_generator.get_rotor_angle(time)
            angle_deviation = generator_angle - other_generator_angle - admittance_angle
            electric_power += voltage_admittance * np.cos(angle_deviation)
            if compute_first_derivative:
                neg_electric_power_derivative += voltage_admittance * np.sin(angle_deviation)

        # Store electric power
        self._generator_electric_powers[generator.name][state][time] = electric_power
        if compute_first_derivative:
            self._neg_generator_electric_power_derivatives[generator.name][state][time] = neg_electric_power_derivative

    @abstractmethod
    def _add_trajectory_point(
        self, generators: Set[DynamicGenerator], from_trajectory_time: GeneratorTrajectoryTime,
        to_trajectory_time: GeneratorTrajectoryTime
    ):
        """
        Add a new trajectory point at a specific time to a set of generators.
        Adding a point consists in computing the value of the generator rotor angle at a specific time moving it from a
        previous point along its trajectory.
        A new rotor angle value is added to each dynamic generator at the specified time.

        :param generators: Dynamic generators whose angle must be computed. They must contain their rotor angle value
                           at time t = from_time.
        :param from_trajectory_time: Time associated to the values of the generator angles at the previous point.
        :param to_trajectory_time: Target time corresponding to the new values of the generator angles to be computed.
        :raise GeneratorInertiaException if a generator has no inertia.
        """
        pass

    def _get_update_time_sequence(
        self, transition_time: float, last_update_time: float, number_during_fault_intervals: int,
        number_post_fault_intervals: int
    ) -> List[GeneratorTrajectoryTime]:
        """
        Get the sequence of update times.

        The time sequence consists in a given number of updates when the network is in the during-fault state and
        another number of updates when it is in the post-fault state.

        :param transition_time: Time (s) at which the network goes from the during-fault state to the post-fault state.
        :param last_update_time: Last update time (s) in the sequence.
        :param number_during_fault_intervals: Number of time intervals in the during-fault state
        :param number_post_fault_intervals: Number of time intervals in the post-fault state.
        """
        # Add initial update
        time_sequence = [GeneratorTrajectoryTime(network_state=self._during_state, time=0)]
        # During-fault
        during_fault_interval = transition_time / number_during_fault_intervals
        for i in range(number_during_fault_intervals - 1):
            time_sequence.append(
                GeneratorTrajectoryTime(
                    network_state=self._during_state,
                    time=(i + 1) * during_fault_interval
                )
            )

        # Add transition time
        if self._transition_time_shift > 0:
            # Transition time must be shifted
            time_sequence.append(GeneratorTrajectoryTime(network_state=self._during_state, time=transition_time))
            self._shifted_transition_time = transition_time + self._transition_time_shift
            time_sequence.append(GeneratorTrajectoryTime(
                network_state=self._post_state,
                time=self._shifted_transition_time)
            )
        else:
            time_sequence.append(GeneratorTrajectoryTime(network_state=self._post_state, time=transition_time))

        # Post-fault
        post_fault_interval = (last_update_time - transition_time) / number_post_fault_intervals
        for i in range(number_post_fault_intervals - 1):
            time_sequence.append(
                GeneratorTrajectoryTime(
                    network_state=self._post_state,
                    time=transition_time + (i + 1) * post_fault_interval
                )
            )
        # Add last update time
        time_sequence.append(GeneratorTrajectoryTime(network_state=self._post_state, time=last_update_time))
        return time_sequence

    def update_generator_angles(
        self, generators: Set[DynamicGenerator], transition_time: float, last_update_time: float,
        number_during_fault_intervals: int, number_post_fault_intervals: int
    ):
        """
        Update the generator rotor angles at specific moments. The first update time is the initial time (t = 0).
        The time sequence consists in a given number of updates when the network is in the during-fault state and
        another number of updates when it is in the post-fault state.
        The angles are assumed to follow a trajectory from their previous value towards their new one between two
        instants of the time sequence. The starting rotor angle value for a generator is its initial rotor angle.
        The trajectory to follow is determined by the network state associated to each element of the time sequence.
        All the generators are reset before processing.

        :param generators: Set of dynamic generators whose angle mus be updated.
        :param transition_time: Time (s) at which the network goes from the during-fault state to the post-fault state.
                                This time must be higher than 0.
        :param last_update_time: Last update time (s) in the sequence, must be higher than the transition time.
        :param number_during_fault_intervals: Number of time intervals in the during-fault state.
        :param number_post_fault_intervals: Number of time intervals in the post-fault state.
        :raise GeneratorTrajectoryUpdateTimeException if the transition time is equal to 0 or higher than the last time.
        """
        # Ensure all generators are reset
        for generator in generators:
            generator.reset()

        if (
            cmath.isclose(transition_time, 0, abs_tol=10e-9) or
            last_update_time < transition_time or
            cmath.isclose(transition_time, last_update_time, abs_tol=10e-9)
        ):
            # Time error
            raise GeneratorTrajectoryUpdateTimeException()

        # Get time sequence
        time_sequence = self._get_update_time_sequence(
            transition_time=transition_time,
            last_update_time=last_update_time,
            number_during_fault_intervals=number_during_fault_intervals,
            number_post_fault_intervals=number_post_fault_intervals
        )

        starting_time = time_sequence[0]
        for time in time_sequence[1:]:
            # Add new rotor angle value to each generator at specified time
            self._add_trajectory_point(
                generators=generators,
                from_trajectory_time=starting_time,
                to_trajectory_time=time
            )
            starting_time = time

        # As the shifted point is only used to compute more precisely the points after the transition time, remove it
        if self._transition_time_shift > 0:
            for generator in generators:
                generator.delete(self._shifted_transition_time)
                # Change the network state for the transition time
                generator.add_network_state(transition_time, self._post_state)

    def generate_generator_angles_plot(self, generators: Set[DynamicGenerator], output_file: str):
        """
        Generate a plot describing the evolution of the generator rotor angles.
        If the path exists, it is replaced.

        :param generators: The set of generators whose angles must be plotted. These generators must have been updated
                           at the same time instants.
        :param output_file: Path to an output file.
        """
        if len(generators) == 0:
            # Nothing to plot
            return

        # Plot design
        rc("font", size=18)
        linewidth = 3

        # Create a figure
        fig, ax = plt.subplots(figsize=(15, 12))
        ax.set(xlabel='Time (ms)', ylabel='Rotor Angle (deg)', title='Generator rotor angles')

        # Get generator time instants
        time_instants = np.array(next(gen for gen in generators).observation_times)

        # Get last angles of each generator (absolute value)
        generator_last_angles = []
        for generator in generators:
            last_angle = generator.get_rotor_angle(time_instants[-1])
            generator_last_angles.append((generator, abs(last_angle)))

        # Get 10 first generators associated to the highest angles
        sorted_generators = [
            gen for gen, _ in sorted(generator_last_angles, reverse=True, key=lambda angle: angle[1])
        ]
        first_generators = set(sorted_generators[:10])

        # Plot
        for generator in sorted_generators:
            angles = [np.rad2deg(generator.get_rotor_angle(time)) for time in time_instants]
            if generator in first_generators:
                plt.plot(time_instants * 1000, angles, linewidth=linewidth, marker='o', label=generator.name)
            else:
                plt.plot(time_instants * 1000, angles, linewidth=linewidth, marker='o', label=None)

        # Create the legend
        plt.legend(loc=(0.025, 0.55))

        # Add a grid
        plt.grid(True, color='lightgray', linestyle='dashed')

        # Save the figure
        plt.savefig(output_file)
        plt.close()
