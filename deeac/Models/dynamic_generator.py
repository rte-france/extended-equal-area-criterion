"""
Dynamic generator wrapper.

:module: dynamic_generator
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deeac.Models.bus import Bus

from deeac.enums import GeneratorSource
from deeac.Models.synchronous_generator import SynchronousGenerator


class DynamicGenerator:
    """
    Generator in a network whose rotor angle can evolve with time.
    """

    def __init__(self, generator: SynchronousGenerator):
        """
        Initialize the dynamic wrapper.

        :param generator: Synchronous generator to wrap.
        :return: Return value.
        """
        # OMIB rationale:
        # The underlying synchronous generator stores the instantaneous machine
        # parameters. This wrapper exists because trajectory-based EEAC steps
        # need time-indexed rotor-angle and angular-speed samples on top of the
        # static machine description.
        #
        # Only synchronous machines get this wrapper, because only they belong
        # to the dynamic rotor-angle side of OMIB.
        self._generator = generator
        self._rotor_angles = {0: generator.rotor_angle}
        self._angular_speeds = {0: 0}

    def __repr__(self):
        """
        Return a readable diagnostic representation.

        :return: Printable representation.
        """
        rotor_angles = ", ".join([f"(t={time}s, \u03B4={angle}rad)" for (time, angle) in self._rotor_angles.items()])
        angular_speeds = ", ".join(
            [f"(t={time}s, \u03C9={speed}p.u.)" for (time, speed) in self._angular_speeds.items()]
        )
        return (
            f"Dynamic generator: Name=[{self._generator.name}] Bus=[{self._generator._bus.name}] "
            f"Connected=[{self._generator.connected}] Rotor Angles=[{rotor_angles}] Angular Speeds=[{angular_speeds}]"
        )

    @property
    def generator(self) -> SynchronousGenerator:
        """
        Return the wrapped synchronous generator.

        :return: Wrapped synchronous generator.
        """
        # The wrapped static machine is still the source of all electrical and
        # inertia information. This wrapper only adds the time dimension used
        # by trajectory-oriented OMIB logic.
        return self._generator

    @property
    def source(self) -> GeneratorSource:
        """
        Return the wrapped generator source.

        :return: Wrapped generator source.
        """
        return self._generator.source

    @property
    def name(self) -> str:
        """
        Return the wrapped generator name.

        :return: Wrapped generator name.
        """
        return self._generator.name

    @property
    def bus(self) -> "Bus":
        """
        Return the wrapped generator bus.

        :return: Wrapped generator bus.
        """
        return self._generator.bus

    @property
    def connected(self) -> bool:
        """
        Return the wrapped generator connection state.

        :return: Wrapped generator connection state.
        """
        return self._generator.connected

    @property
    def active_power(self) -> float:
        """
        Return the wrapped generator active power.

        :return: Wrapped generator active power.
        """
        return self._generator.active_power

    @property
    def mechanical_power(self) -> float:
        """
        Return the wrapped generator mechanical power.

        :return: Wrapped generator mechanical power.
        """
        return self._generator.mechanical_power

    @property
    def internal_voltage(self) -> complex:
        """
        Return the wrapped generator internal voltage.

        :return: Wrapped generator internal voltage.
        """
        return self._generator.internal_voltage

    @property
    def inertia_coefficient(self) -> float:
        """
        Return the wrapped generator inertia coefficient.

        :return: Wrapped generator inertia coefficient.
        """
        return self._generator.inertia_coefficient

    def add_rotor_angle(self, time: float, rotor_angle: float):
        """
        Store a rotor angle sample.

        :param time: Observation time in seconds.
        :param rotor_angle: Rotor angle in radians.
        :return: Return value.
        """
        # Rotor-angle samples are what eventually allow OMIB/EAC logic to ask:
        # "at this instant, where is the synchronous machine relative to the
        # cluster center?"
        self._rotor_angles[time] = rotor_angle

    def get_rotor_angle(self, time: float) -> float:
        """
        Return the rotor angle at a given time.

        :param time: Observation time in seconds.
        :return: Rotor angle in radians.
        """
        return self._rotor_angles[time]

    def add_angular_speed(self, time: float, angular_speed: float):
        """
        Store an angular-speed sample.

        :param time: Observation time in seconds.
        :param angular_speed: Angular speed in per unit.
        :return: Return value.
        """
        # Angular speed is stored alongside angle because trajectory-based
        # stability logic can need both the position and the motion of the
        # synchronous source in the OMIB world.
        self._angular_speeds[time] = angular_speed

    def get_angular_speed(self, time: float) -> float:
        """
        Return the angular speed at a given time.

        :param time: Observation time in seconds.
        :return: Angular speed in per unit.
        """
        return self._angular_speeds[time]

    @property
    def observation_times(self):
        """
        Return all observation times.

        :return: Observation time set.
        """
        return set(self._rotor_angles.keys())
