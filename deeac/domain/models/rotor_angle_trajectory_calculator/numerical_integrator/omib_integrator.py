# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Tuple
from scipy.integrate import solve_ivp
from deeac.domain.models import NetworkState
from deeac.domain.models.omib import OMIB
from deeac.domain.models.rotor_angle_trajectory_calculator import (
    OMIBRotorAngleTrajectoryCalculator, OMIBTrajectoryPoint, OMIBTrajectoryAngle
)
from deeac.domain.exceptions import OMIBInertiaException, RotorAngleTimeException


# Maximum integration time (s) that should be higher than the maximum time.
MAXIMUM_INTEGRATION_TIME = 10


def _swing_equation(
    state_vector: Tuple[float, float], omib: OMIB, state: NetworkState) -> Tuple[float, float]:
    """
    Representation of the swing equation for an OMIB.
    This functions derives the rotor angle and angular speed derivatives of the machine.

    :param state_vector: Tuple representing the rotor angle value (rad) and the angular speed (rad/s).
    :param omib: OMIB to which the swing equation applies.
    :param state: Network state to consider for the OMIB trajectory.
    :return: The vector of the rotor angle and angular speed derivatives.
    """
    rotor_angle, angular_speed = state_vector
    rotor_angle_derivative = omib.network.pulse * angular_speed
    electric_power = omib.get_electric_power(rotor_angle, state)
    angular_speed_derivative = (1 / omib.inertia) * (omib.mechanical_power - electric_power)
    return rotor_angle_derivative, angular_speed_derivative


def _angle_event(
    state_vector: Tuple[float, float],angle: float) -> float:
    """
    Event function allowing to identify the time corresponding to a specific angle.
    The solver will find an accurate value of t at which event(t, state_vector[0](t)) = angle using a root-finding
    algorithm.

    :param state_vector: Tuple representing the rotor angle value (rad) and the angular speed (rad/s).
    :param angle: Angle (rad) for which the time must be found.
    :return: The difference between the angle in the state vector and the target angle.
    """
    return state_vector[0] - angle


# Set terminal attribute of event so that integration ends as soon as event occurs.
_angle_event.terminal = True


class OMIBNumericalIntegrator(OMIBRotorAngleTrajectoryCalculator):
    """
    Class able to derive the rotor angle of an OMIB at a specific time based on numerical integration.
    """

    def _get_trajectory_point(
        self, from_point: OMIBTrajectoryPoint, to_angle: OMIBTrajectoryAngle
    ) -> OMIBTrajectoryPoint:
        """
        Compute a new trajectory point containing the time needed for the rotor angle to move from the point from_point
        to the angle to_angle.

        :param from_point: Initial point on the trajectory.
        :param to_angle: Target angle on the trajectory.
        :return: A new trajectory point containing the time the rotor angle needs to move from point from_point to angle
                to_angle.
        :raise: OMIBInertiaException if the OMIB has no inertia.
        """
        if self.omib.inertia == 0:
            # OMIB has no inertia cannot go further
            raise OMIBInertiaException(self.omib)

        # Solve differential system
        integration_interval = (from_point.time, MAXIMUM_INTEGRATION_TIME)
        initial_state = (from_point.angle, from_point.angular_speed)
        solution = solve_ivp(
            fun=_swing_equation,
            t_span=integration_interval,
            y0=initial_state,
            method="LSODA",
            args=(self.omib, from_point.network_state, to_angle.angle),
            events=_angle_event
        )
        if solution.status != 1:
            # Integration failed
            raise RotorAngleTimeException(to_angle.angle)

        # Get time and corresponding angular speed
        time = solution.t_events[0][0]
        angular_speed = solution.y_events[0][0][1]

        return OMIBTrajectoryPoint(
            network_state=to_angle.network_state,
            angle=to_angle.angle,
            time=time,
            angular_speed=angular_speed
        )
