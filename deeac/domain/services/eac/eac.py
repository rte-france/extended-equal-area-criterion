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
import matplotlib.pyplot as plt
from typing import Tuple
from matplotlib import rc
from enum import Enum

from deeac.domain.models.omib import OMIB, OMIBStabilityState, OMIBSwingState
from deeac.domain.models import NetworkState
from deeac.domain.exceptions import DEEACException


class EAC:
    """
    Service able to apply the Equal Area Criterion (EAC) to determine the critical clearing angle of a power system in a
    transient stability study.
    """

    def __init__(self,
                 omib: OMIB,
                 angle_increment: float = np.pi / 1800,
                 max_integration_angle: float = 2 * np.pi,
                 exploration_angle_increment_factor: int = 15,
                 exploration_last_angle_increment_factor: int = 20):
        """
        Initialize the EAC service.

        :param omib: OMIB to use in this EAC computation.
        :param angle_increment: Angle increment to consider (rad) during critical angle search.
        :param max_integration_angle: Maximum OMIB integration angle (rad).
        """
        # Initialize states for performances
        self._pre_state = NetworkState.PRE_FAULT
        self._during_state = NetworkState.DURING_FAULT
        self._post_state = NetworkState.POST_FAULT

        # OMIB and swing state
        self._omib = omib
        self._swing_factor = -1 if omib.swing_state == OMIBSwingState.BACKWARD else 1

        # Increment for critical angle search
        self._angle_increment = angle_increment
        self._exploration_angle_increment_factor = exploration_angle_increment_factor
        self._exploration_last_angle_increment_factor = exploration_last_angle_increment_factor

        # Maximum integration angle
        self._max_integration_angle = max_integration_angle

        # Results
        self._critical_clearing_angle = None
        self._maximum_angle = None

    def _get_trajectory_power_area(self, from_rotor_angle: float, to_rotor_angle: float, state: NetworkState,
                                   angle_shift: float, constant_electric_power: float,
                                   maximum_electric_power: float) -> float:
        """
        Compute the power area between two OMIB rotor angles based on the trajectory corresponding to the provided
        network state.

        :param from_rotor_angle: Starting angle (rad).
        :param to_rotor_angle: Ending angle (rad).
        :param state: Network state to consider for the rotor angle trajectory. Only during and post-fault states are
                      allowed.
        :param angle_shift: Precomputed angle shift.
        :param constant_electric_power: Precomputed constant electric power.
        :param maximum_electric_power: Precomputed maximum electric power.
        :return: The area between from_angle and to_angle along the OMIB trajectory.
        """
        # Compute area
        power_difference = self._omib.mechanical_power - constant_electric_power
        cosine_difference = np.cos(to_rotor_angle - angle_shift) - np.cos(from_rotor_angle - angle_shift)
        first_term = power_difference * (to_rotor_angle - from_rotor_angle)
        second_term = maximum_electric_power * cosine_difference
        return first_term + second_term

    def _get_power_area(self, from_rotor_angle: float, to_rotor_angle: float, state: NetworkState) -> float:
        """
        Get the power area of the OMIB when its angle move from a specified value to a final one.
        This function sums multiple areas along different OMIB trajectories if the OMIB was updated at different points.

        :param from_rotor_angle: Starting angle (rad) from which the OMIB angle will move.
        :param to_rotor_angle: Final angle (rad) to which the OMIB angle will move.
        :param state: Network state to consider for the rotor angle trajectory. Only during and post-fault states are
                      allowed.
        """
        update_angles = [angle for angle, _, network_state in self._omib.update_angles if network_state == state]

        # Retrieve the OMIB properties once for all the angles in the range
        angle_shift, constant_electric_power, maximum_electric_power \
            = self._omib.get_properties(state, from_rotor_angle)

        start_angle = from_rotor_angle
        area = 0
        for update_angle in update_angles[1:]:
            if update_angle * self._swing_factor < from_rotor_angle * self._swing_factor:
                # Do not consider updates before starting angle
                continue
            if update_angle * self._swing_factor > to_rotor_angle * self._swing_factor:
                # Do not consider updates after ending rotor angle
                break

            area += self._get_trajectory_power_area(start_angle, update_angle, state, angle_shift,
                                                    constant_electric_power, maximum_electric_power)
            start_angle = update_angle

        # Add last area to the final angle
        area += self._get_trajectory_power_area(start_angle, to_rotor_angle, state, angle_shift,
                                                constant_electric_power, maximum_electric_power)
        return area

    def _get_critical_and_maximum_angles(self) -> Tuple[float, float]:
        """
        Compute the critical clearing angle and the maximum angle based on the OMIB curves.
        The critical angle is the one for which the acceleration and deceleration areas are almost equal.

        :return: A tuple containing respectively the critical clearing angle and the maximum angle (rad).
        """
        # Define the angle increment based on the swing state
        angle_increment = self._angle_increment * self._swing_factor
        big_angle_increment = angle_increment * self._exploration_angle_increment_factor
        big_last_angle_increment = angle_increment * self._exploration_last_angle_increment_factor
        # Current rotor angle and last angle to consider when computing deceleration area
        angle = self._omib.initial_rotor_angle
        last_angle = angle + big_angle_increment

        # Candidate critical and maximum angles
        candidate_cc_angle = self._omib.initial_rotor_angle
        candidate_maximum_angle = self._omib.initial_rotor_angle

        # Find last possible candidate critical angle, as it will be the critical one
        acceleration_area = 0
        angle_exploration_mode = True

        while angle * self._swing_factor < self._max_integration_angle:
            # Get angle at which areas are similar, as it is a candidate
            last_angle_exploration_mode = True
            while last_angle * self._swing_factor <= self._max_integration_angle:
                deceleration_area = self._get_power_area(
                    angle,
                    last_angle,
                    self._post_state
                )
                if acceleration_area + deceleration_area <= 0:
                    if last_angle_exploration_mode:
                        last_angle_exploration_mode = False
                        last_angle -= big_last_angle_increment
                    else:
                        # Found the point where area are (almost) similar -> new candidate found
                        candidate_cc_angle = angle
                        candidate_maximum_angle = last_angle
                        break
                if last_angle_exploration_mode:
                    last_angle += big_last_angle_increment
                else:
                    last_angle += angle_increment

            if last_angle * self._swing_factor > self._max_integration_angle:
                # No new candidate was found
                if candidate_cc_angle == self._omib.initial_rotor_angle:
                    # Always unstable case
                    self._omib.stability_state = OMIBStabilityState.ALWAYS_UNSTABLE
                    return (
                        self._omib.initial_rotor_angle,
                        self._omib.initial_rotor_angle
                    )
                electric_power = self._omib.get_electric_power(
                    candidate_maximum_angle,
                    self._post_state
                )
                if self._swing_factor * self._omib.mechanical_power <= self._swing_factor * electric_power:
                    if angle_exploration_mode:
                        angle_exploration_mode = False
                        angle = angle - big_angle_increment
                    else:
                        # Candidate angle is the critical one
                        self._omib.stability_state = OMIBStabilityState.POTENTIALLY_STABLE
                        return (
                            candidate_cc_angle,
                            candidate_maximum_angle
                        )

            # Try to determine if another candidate exists
            if angle_exploration_mode:
                angle += big_angle_increment
            else:
                angle += angle_increment
            last_angle = angle + big_angle_increment

            # Update acceleration area
            acceleration_area = self._get_power_area(
                self._omib.initial_rotor_angle,
                angle,
                self._during_state
            )

        # Did not find any candidate -> always stable
        self._omib.stability_state = OMIBStabilityState.ALWAYS_STABLE
        max_integration_angle = self._max_integration_angle * self._swing_factor
        return max_integration_angle, max_integration_angle

    @property
    def omib(self) -> OMIB:
        """
        Return the OMIB used by EAC.

        return: The OMIB used by EAC.
        """
        return self._omib

    @property
    def critical_clearing_angle(self) -> float:
        """
        Get the critical clearing angle for the network and the list of events.

        :return: The critical clearing angle (rad).
        """
        if self._critical_clearing_angle is None:
            self._critical_clearing_angle, self._maximum_angle = self._get_critical_and_maximum_angles()
        return self._critical_clearing_angle

    @property
    def maximum_angle(self) -> float:
        """
        Get the maximum angle that can be reached by the OMIB.

        :return: The maximum angle (rad).
        """
        if self._maximum_angle is None:
            self._critical_clearing_angle, self._maximum_angle = self._get_critical_and_maximum_angles()
        return self._maximum_angle

    def generate_area_plot(self, output_file: str):
        """
        Generate the representation of the equal area criterion applied on the network.
        This representation is outputed as a graph in a file.
        If the path exists, it is replaced.
        If the critical angle cannot be computed, only electric powers based on intial angles are plotted.
        Only the first forward or backward swing is represented.

        :param output_file: Path to an output file.
        """
        plot_only_initial_electric_powers = False
        if self._critical_clearing_angle is None:
            # Run algorithm to get critical clearing angle
            try:
                self.critical_clearing_angle
            except DEEACException:
                # Plot only electric powers to observe why a critical angle could not be found
                plot_only_initial_electric_powers = True

        potentially_stable = True
        if self._omib.stability_state != OMIBStabilityState.POTENTIALLY_STABLE:
            # OMIB is not potentially stable
            potentially_stable = False

        # Plot design
        rc("font", size=16)
        linewidth = 3
        green = "#24965d"
        orange = "#E6743E"
        light_grey = "#B0B0B0"
        blue = "#00609A"
        black = "#000000"

        # Create a figure
        _, ax = plt.subplots(figsize=(15, 12))
        ax.set(xlabel='Rotor Angle (deg)', ylabel='Power (p.u.)', title='Representation of equal area criterion')

        # Sample rotor angle
        during_fault_angle_shift, _, _ = self._omib.get_properties(self._during_state)
        post_fault_angle_shift, _, _ = self._omib.get_properties(self._post_state)
        min_shift, max_shift = sorted((during_fault_angle_shift, post_fault_angle_shift))
        if self.omib.swing_state == OMIBSwingState.FORWARD:
            rotor_angles = np.arange(min_shift, np.pi + max_shift, np.pi / 100)
        else:
            # Backswing instability
            rotor_angles = np.arange(max_shift, min_shift - np.pi, -np.pi / 100)
        rotor_angles_deg = [np.rad2deg(angle) for angle in rotor_angles]

        # Plot mechanical power
        mechanical_power = self._omib.mechanical_power
        plt.axhline(y=mechanical_power, linewidth=linewidth, color=light_grey)

        # Plot electric powers based on initial angles
        omib_colors = {
            self._pre_state: green,
            self._during_state: orange,
            self._post_state: blue
        }
        for state, color in omib_colors.items():
            angle_shift, constant_electric_power, maximum_electric_power = self._omib.get_properties(state)
            power = constant_electric_power + maximum_electric_power * np.sin(rotor_angles - angle_shift)
            plt.plot(rotor_angles_deg, power, linewidth=linewidth - 0.5, color=color, linestyle='dashed')

        if not plot_only_initial_electric_powers:
            # Initial rotor angle
            initial_angle = self.omib.initial_rotor_angle

            # Get update angles until the maximum angle
            if potentially_stable:
                omib_angles = [
                    angle for angle in self._omib.update_angles if
                    self._swing_factor * angle[0] < self._swing_factor * self._maximum_angle
                ]
                # Add critical clearing and maximum angles
                omib_angles.append((self._critical_clearing_angle, None, self._post_state))
                omib_angles.append((self._maximum_angle, None, self._post_state))
            else:
                omib_angles = [
                    (angle, time, state) for angle, time, state in self._omib.update_angles
                    if time != 0 or state == NetworkState.DURING_FAULT
                ]

            # Sort angles and get their associated state
            current_state = self._during_state
            angles = []
            sorted_angles = sorted(omib_angles, key=lambda angle: angle[0] * self._swing_factor)
            for omib_angle in sorted_angles:
                angle, _, state = omib_angle
                if potentially_stable:
                    # Case potentially stable, search for clearing angle
                    if cmath.isclose(angle, self._critical_clearing_angle, abs_tol=10e-9):
                        current_state = self._post_state
                    if state != current_state:
                        # Ignore points that do not have the same state
                        continue
                angles.append((angle, state))

            from_angle, state = angles[0]
            for to_angle, next_state in angles[1:]:
                # Sample rotor angles
                rotor_angles_sample = np.arange(from_angle, to_angle, self._swing_factor * np.pi / 100)
                rotor_angles_sample_deg = [np.rad2deg(angle) for angle in rotor_angles_sample]

                # Compute electric power
                angle_shift, constant_electric_power, maximum_electric_power = self._omib.get_properties(
                    state,
                    from_angle
                )
                power = constant_electric_power + maximum_electric_power * np.sin(rotor_angles_sample - angle_shift)

                # Plot power in the interval
                color = omib_colors[state]
                plt.plot(rotor_angles_sample_deg, power, linewidth=linewidth + 1.5, color=color)

                # Fill area
                fill_condition = (
                    (self._swing_factor * rotor_angles_sample >= self._swing_factor * from_angle) &
                    (self._swing_factor * rotor_angles_sample < self._swing_factor * to_angle)
                )
                if potentially_stable:
                    plt.fill_between(
                        rotor_angles_sample_deg,
                        mechanical_power,
                        power,
                        where=fill_condition,
                        color=color,
                        alpha=0.2
                    )

                # Update from angle and state
                from_angle = to_angle
                state = next_state

            # Plot critical, initial and maximum angles
            ymin, ymax = plt.ylim()
            ymax = (mechanical_power - ymin) / (ymax - ymin)
            if potentially_stable:
                cc_angle = np.rad2deg(self._critical_clearing_angle)
                plt.axvline(x=cc_angle, linewidth=linewidth, color=black, linestyle='dashed')
                plt.text(cc_angle + 0.7, ymin + 0.4, f"$\\delta_c = {cc_angle:.3f}$")

                maximum_angle = np.rad2deg(self._maximum_angle)
                plt.axvline(
                    x=maximum_angle,
                    ymax=ymax,
                    linewidth=1,
                    color=black,
                    linestyle='dashed'
                )
            plt.axvline(
                x=np.rad2deg(initial_angle),
                ymax=ymax,
                linewidth=1,
                color=black,
                linestyle='dashed'
            )

            # Write label for initial and maximum angles
            initial_angle = np.rad2deg(initial_angle)
            if self.omib.swing_state == OMIBSwingState.FORWARD:
                plt.text(initial_angle - 25, ymin + 0.4, f"$\\delta_0 = {initial_angle:.3f}$")
            else:
                plt.text(initial_angle + 0.7, ymin + 0.4, f"$\\delta_0 = {initial_angle:.3f}$")
            if potentially_stable:
                plt.text(maximum_angle + 0.7, ymin + 0.4, f"$\\delta_m = {maximum_angle:.3f}$")

        # Write label for mechanical power
        xmin, _ = plt.xlim()
        plt.text(
            xmin + 0.7,
            self._omib.mechanical_power + 0.5,
            f"$P_m = {self._omib.mechanical_power:.3f}$"
        )

        # Create the legend
        plt.legend(
            [
                "Mechanical power",
                "Pre-fault electric power",
                "During-fault electric power",
                "Post-fault electric power"
            ],
            loc="best"
        )

        # Add a grid
        plt.grid(True, color='lightgray', linestyle='dashed')

        # Save the figure
        plt.savefig(output_file)
        plt.close()
