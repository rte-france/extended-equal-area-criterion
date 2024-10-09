# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import cmath
from typing import List
from abc import ABC, abstractmethod

import numpy as np
from pydantic import BaseModel

from deeac.domain.models import NetworkState
from deeac.domain.models.omib import OMIB
from deeac.domain.models.omib.omib import OMIBSwingState
from deeac.domain.exceptions import RotorAngleTimeException


class OMIBTrajectoryPoint(BaseModel):
    """
    Representation of a point on the OMIB rotor angle trajectory.

    :param state: Network state considered starting from this point (i.e. in the future).
    :param time: Time (seconds) corresponding to the point on the trajectory (starting from initial time).
    :param angle: OMIB angle (rad) corresponding to the point on the trajectory.
    :param angular_speed: OMIB angular speed (rad/s) at the point.
    """
    network_state: NetworkState
    time: float
    angle: float
    angular_speed: float


class OMIBTrajectoryAngle(BaseModel):
    """
    Specific angle on the trajectory.

    :param state: Network state to consider on the trajectory from this angle (i.e. in the future).
    :param angle: OMIB angle (rad) on the trajectory.
    """
    network_state: NetworkState
    angle: float


class OMIBRotorAngleTrajectoryCalculator(ABC):
    """
    Compute the time between two points on the rotor angle trajectory.
    """

    def __init__(self, omib: OMIB, transition_angle_shift: float = 0):
        """
        Initialize the trajectory calculator.

        :param omib: OMIB to use with this calculator.
        :param transition_angle_shift: Positive shift (rad) to apply to the transition angle. It is only used to compute
                                       the times associated to the angles greater than the transition angle, allowing to
                                       obtain an improved curve in further analyses. The time outputted for the
                                       transition angle is not altered by this shift.
        """
        self._omib = omib
        self._transition_angle_shift = transition_angle_shift

        # Check swing state and
        if omib.swing_state == OMIBSwingState.BACKWARD:
            self._swing_factor = -1
            self._select_angle = max
        else:
            self._swing_factor = 1
            self._select_angle = min

        # Initialize states to improve performances
        self._during_state = NetworkState.DURING_FAULT
        self._post_state = NetworkState.POST_FAULT

        # Get update angles
        self._update_angles = [angle for angle in omib.update_angles if angle[0] != omib.initial_rotor_angle]

    @property
    def omib(self) -> OMIB:
        """
        Get the OMIB used with this calculator.

        :return: The OMIB used with this trajectory calculator.
        """
        return self._omib

    @omib.setter
    def omib(self, omib: OMIB):
        """
        Provide a new OMIB to this calculator.

        :param omib: New OMIB to use.
        """
        self._omib = omib

    @abstractmethod
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
        """
        pass

    def get_trajectory_times(self, angles: List[float], transition_angle: float) -> List[float]:
        """
        Compute times the OMIB needs to reach specific angles, considering the machine moves from its initial angle.
        The OMIB is assumed to follow its rotor angle trajectory based on the during and post-fault states.
        The transition between the during and post-fault states is assumed to occur at the transition angle.

        :param angles: Sorted list of OMIB angles for which the time instants must be derived.
        :param transition_angle: Angle (rad) at which the OMIB switchs from its during-fault to its post-fault state.
        :return: List of the times associated to the specified angles.
        """
        if not angles:
            # Empy list
            return []

        # Shift transition angle
        transition_angle += self._transition_angle_shift * self._swing_factor

        # Create starting point
        from_point = OMIBTrajectoryPoint(
            network_state=self._during_state,
            time=0,
            angle=self.omib.initial_rotor_angle,
            angular_speed=0
        )
        current_state = self._during_state

        # First angle
        angle_iterator = iter(angle for angle in angles)
        angle = next(angle_iterator)
        # First update angle
        update_angle_iterator = iter(update_angle for update_angle in self._update_angles)
        try:
            update_angle, _, _ = next(update_angle_iterator)
        except StopIteration:
            update_angle = None

        # Elapsed times
        times = []
        while angle is not None:
            get_next_angle = False
            angle_list = [angle]
            if update_angle is not None:
                angle_list.append(update_angle)
            if current_state == self._during_state:
                # Transition angle not considered yet
                angle_list.append(transition_angle)
            target_angle = self._select_angle(angle_list)

            if cmath.isclose(target_angle, angle):
                # Angle is next target
                target_state = from_point.network_state
                get_next_angle = True
            if update_angle is not None and cmath.isclose(target_angle, update_angle):
                # Update angle is next state
                target_state = current_state
                try:
                    update_angle, _, _ = next(update_angle_iterator)
                except StopIteration:
                    update_angle = None
            if current_state == self._during_state and cmath.isclose(target_angle, transition_angle):
                # Transition angle is next target
                target_state = self._post_state
                current_state = self._post_state

            try:
                to_point = self._get_trajectory_point(
                    from_point=from_point,
                    to_angle=OMIBTrajectoryAngle(
                        network_state=target_state,
                        angle=target_angle
                    )
                )
            # Try again by reducing the angle slightly
            except RotorAngleTimeException:
                try:
                    if target_angle != 0:
                        angle_reduction = np.sign(target_angle) * abs(target_angle - self.omib.initial_rotor_angle) / 10
                    else:
                        angle_reduction = - self.omib.initial_rotor_angle / 10

                    to_point = self._get_trajectory_point(
                        from_point=from_point,
                        to_angle=OMIBTrajectoryAngle(
                            network_state=target_state,
                            angle=target_angle - angle_reduction
                        )
                    )
                except RotorAngleTimeException as error:
                    raise error

            if get_next_angle:
                try:
                    # Keep time value for previous point
                    times.append(to_point.time)
                    angle = next(angle_iterator)
                except StopIteration:
                    angle = None

            # Update from point
            from_point = to_point

        return times
