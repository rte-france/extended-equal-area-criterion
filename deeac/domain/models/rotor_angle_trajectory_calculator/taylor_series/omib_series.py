# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List, Tuple
import numpy as np

from deeac.domain.models import NetworkState
from deeac.domain.models.rotor_angle_trajectory_calculator import (
    OMIBRotorAngleTrajectoryCalculator, OMIBTrajectoryPoint, OMIBTrajectoryAngle
)
from deeac.domain.exceptions import OMIBInertiaException, RotorAngleTimeException


class OMIBTaylorSeries(OMIBRotorAngleTrajectoryCalculator):
    """
    Class modeling a Global Taylor Series as an OMIB rotor angle trajectory calculator.
    """

    def _get_angular_speed_derivatives(
        self, angular_speed: float, rotor_angle: float, state: NetworkState
    ) -> Tuple[float, float, float, float]:
        """
        Compute the four first time derivatives of the angular speed for the OMIB in the specified state.

        :param angular_speed: Angular speed (rad/s) of the OMIB.
        :param rotor_angle: Rotor angle (rad) at which the derivatives must be computed.
        :param state: State of the OMIB to consider.
        :return: A tuple with respectively the first, second, third and fourth time derivatives.
        """
        # Get OMIB properties
        angle_shift, constant_electric_power, maximum_electric_power = self.omib.get_properties(state, rotor_angle)

        # Compute angle deviation
        angle_deviation = rotor_angle - angle_shift

        # Compute power terms
        inertia_inverse = 1 / self.omib.inertia
        power_term = inertia_inverse * maximum_electric_power
        power_sine = power_term * np.sin(angle_deviation)
        power_cosine = power_term * np.cos(angle_deviation)

        # First derivative
        network_pulse = self.omib.network.pulse
        first_derivative = inertia_inverse * (self.omib.mechanical_power - constant_electric_power) - power_sine

        # Second derivative
        second_derivative = -power_cosine * angular_speed * network_pulse

        # Third derivative
        angular_speed_second = angular_speed * angular_speed
        network_pulse_second = network_pulse * network_pulse
        third_derivative = (
            power_sine * angular_speed_second * network_pulse_second - first_derivative * power_cosine * network_pulse
        )

        # Fourth derivative
        angular_speed_third = angular_speed * angular_speed_second
        network_pulse_third = network_pulse * network_pulse_second
        fourth_derivative = (
            power_cosine * (network_pulse_third * angular_speed_third - network_pulse * second_derivative) +
            3 * power_sine * network_pulse_second * angular_speed * first_derivative
        )

        return first_derivative, second_derivative, third_derivative, fourth_derivative

    @staticmethod
    def _get_positive_real_roots(coefficients: List[float]) -> List[float]:
        """
        Get the positive and real roots of a polynomial equation.

        :param coefficients: List of the polynomial coefficients (highest order to lowest).
        :return: The list of positive real roots.
        """
        roots = np.roots(coefficients)
        return [root.real for root in roots if root.imag == 0 and root.real >= 0]

    def _get_trajectory_point(
        self, from_point: OMIBTrajectoryPoint, to_angle: OMIBTrajectoryAngle
    ) -> OMIBTrajectoryPoint:
        """
        Compute a new trajectory point containing the time needed for the rotor angle to move from the point from_point
        to the angle to_angle.

        :param from_point: Initial point on the trajectory.
        :param to_angle: Target angle on the trajectory.
        :return A new trajectory point containing the time the rotor angle needs to move from point from_point to angle
                to_angle.
        :raise: OMIBInertiaException if the OMIB has no inertia.
        """
        if self.omib.inertia == 0:
            # OMIB has no inertia cannot go further
            raise OMIBInertiaException(self.omib)

        # Compute network pulse
        network_pulse = self.omib.network.pulse

        # Get angular speed derivatives at from point
        first_derivative, second_derivative, third_derivative, fourth_derivative = (
            self._get_angular_speed_derivatives(
                angular_speed=from_point.angular_speed,
                rotor_angle=from_point.angle,
                state=from_point.network_state
            )
        )

        # Get all polynomial coefficients
        coefficients = [
            third_derivative * network_pulse / 24,
            second_derivative * network_pulse / 6,
            first_derivative * network_pulse / 2,
            from_point.angular_speed * network_pulse,
            from_point.angle - to_angle.angle
        ]

        # Solve equations
        max_order_roots = []
        for i in range(0, 4):
            # Search for roots with series of highest order
            max_order_roots = self._get_positive_real_roots(coefficients[i:])
            if len(max_order_roots) > 0:
                break
        nb_roots = len(max_order_roots)
        if nb_roots == 0:
            # Root could not be computed
            raise RotorAngleTimeException(to_angle.angle)
        elif nb_roots == 1:
            root = max_order_roots[0]
        else:
            other_root = None
            for i in range(2, 4):
                # Try to compare to root from second or first order
                other_roots = self._get_positive_real_roots(coefficients[i:])
                if len(other_roots) == 1:
                    other_root = other_roots[0]
                    break
            if other_root is None:
                # TODO: clever solution?
                # Take minimum root to be the most restrictive
                root = min(max_order_roots)
            else:
                # Take closest root to the other root
                root = min(max_order_roots, key=lambda x: abs(x - other_root))

        # Compute angular speed at target point with Taylor
        time = root  # Elapsed time between from angle and target angle
        time_second = time * time
        time_third = time * time_second
        time_fourth = time * time_third
        to_angular_speed = (
            from_point.angular_speed +
            first_derivative * time +
            second_derivative * time_second / 2 +
            third_derivative * time_third / 6 +
            fourth_derivative * time_fourth / 24
        )

        return OMIBTrajectoryPoint(
            network_state=to_angle.network_state,
            time=from_point.time + root,
            angle=to_angle.angle,
            angular_speed=to_angular_speed
        )
