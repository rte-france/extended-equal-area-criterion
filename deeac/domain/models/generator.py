# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Dict, List, TYPE_CHECKING
import numpy as np
from enum import Enum

from deeac.domain.exceptions import (
    DisconnectedElementException, ZeroDirectTransientReactanceException, UnknownRotorAngleException,
    UnknownAngularSpeedException, UnknownNetworkStateException
)
if TYPE_CHECKING:
    from .bus import Bus
    from .network import NetworkState


class GeneratorType(Enum):
    PQ = "PQ"
    PV = "PV"
    SLACK = "SLACK"


class GeneratorSource(Enum):
    nucleair = "NUCLEAR"
    photovol = "SOLAR"
    step = "HYDRO"
    charbon = "COAL"
    eolien = "WIND"
    fictif = "FICTIVE"
    fuel = "OIL"
    turbinag = "HYDRO"
    tag = "GAS"
    pompage = "HYDRO"
    autre = "OTHER"
    cycle_co = "CYCLE"
    none = "NONE"
    unknown = "UNKNOWN"


class Generator:
    """
    Generator in a network.
    """

    def __init__(
        self, name: str, type: GeneratorType, bus: 'Bus',
        pu_base_reactance, base_power,
        direct_transient_reactance: float, inertia_constant: float,
        active_power: float, max_active_power: float,
        reactive_power: float,
        connected: bool = True, source: GeneratorSource = None
    ):
        """
        Initialize a generator.

        :param name: Name of the generator.
        :param type: Type of generator (PV or PQ).
        :param bus: Bus to which the generator is connected.
        :param direct_transient_reactance: Direct axis transient reactance of the generator. Unit: Ohm.
        :param inertia_constant: Constant of inertia of the generator. Unit: MWs / MVA
        :param active_power: Active power of the generator. Unit: MW.
        :param max_active_power: Maximum active power of the generator. Unit: MW.
        :param reactive_power: Reactive power of the generator. Unit: MVAr.
        :param target_voltage_magnitude: Target voltage magnitude applied by the generator in case of a PV generator.
        :param connected: True if the generator is connected to the network, False otherwise.
        :raise ZeroDirectTransientReactanceExeption if direct transient reactance is equal to 0.
        """
        self.name = name
        self.type = type
        self._bus = bus

        self._pu_base_reactance = pu_base_reactance
        self._base_power = base_power

        self._direct_transient_reactance_pu = direct_transient_reactance / pu_base_reactance
        self._inertia_constant = inertia_constant

        self._active_power_pu = active_power / base_power
        self._max_active_power_pu = max_active_power / base_power
        self._reactive_power_pu = reactive_power / base_power

        self.connected = connected
        self.source = source

        # Compute properties
        self._complex_power = complex(self._active_power_pu, self._reactive_power_pu)
        try:
            self._direct_transient_admittance = 1 / complex(0, self._direct_transient_reactance_pu)
        except ZeroDivisionError:
            raise ZeroDirectTransientReactanceException(name)
        self.compute_internal_voltage()

    def __repr__(self):
        """
        Representation of a generator.
        """
        return (
            f"Generator: Name=[{self.name}] Type=[{self.type.name}] Bus=[{self._bus.name}] "
            f"x'd=[{self.direct_transient_reactance}] H=[{self._inertia_constant}] "
            f"P=[{self.active_power}] Pmax=[{self.max_active_power}]  "
            f"Q=[{self.reactive_power}] "
            f"Connected=[{self.connected}]"
        )

    def compute_internal_voltage(self):
        """
        Compute the internal voltage of this generator.
        """
        from deeac.domain.models import BusType
        if self._bus.type == BusType.GEN_INT_VOLT:
            # Generator is connected to a fictive bus representing its internal voltage
            self._internal_voltage = self._bus.voltage
            return
        if self._bus.voltage == 0j:
            # Bus voltage is zero (disconnected from network)
            self._internal_voltage = 0j
            return
        # Compute conjugate of internal current (I = S / V)
        conj_current = np.conj(self._complex_power / self._bus.voltage)
        # E = V + jXI
        self._internal_voltage = complex(self._bus.voltage, self._direct_transient_reactance_pu * conj_current)
        # Get rotor angle
        self._rotor_angle = np.angle(self._internal_voltage)

    @property
    def bus(self) -> 'Bus':
        """
        Return the bus to the generator it is connected with

        :return: Thus connected bus.
        """
        return self._bus

    @bus.setter
    def bus(self, bus: 'Bus'):
        """
        Change the bus connected to the generator.

        :param bus: The new bus to which the generator is connected.
        """
        self._bus = bus
        self.compute_internal_voltage()

    @property
    def max_active_power_pu(self) -> float:
        """
        Return the maximum active power in per unit.
        """
        return self._max_active_power_pu

    @property
    def max_active_power(self) -> float:
        """
        Return the maximum active power in MW.
        """
        return self._max_active_power_pu * self._base_power

    @property
    def active_power_pu(self) -> float:
        """
        Return the active power in per unit.
        """
        return self._active_power_pu

    @property
    def active_power(self) -> float:
        """
        Return the active power value.

        :return: The active power value in MW.
        """
        return self._active_power_pu * self._base_power

    @property
    def reactive_power(self) -> float:
        """
        Return the reactive power value.

        :return: The reactive power value in MVAr.
        """
        return self._reactive_power_pu * self._base_power

    @property
    def direct_transient_reactance_pu(self) -> float:
        """
        Return the direct transient reactance in per unit

        :return: Direct transient reactance in per unit.
        :raise DisconnectedElementException if the generator is disconnected.
        """
        if not self.connected:
            raise DisconnectedElementException(repr(self), Generator.__name__)
        return self._direct_transient_reactance_pu

    @property
    def direct_transient_reactance(self) -> float:
        """
        Return the direct transient reactance

        :return: Direct transient reactance in Ohm.
        :raise DisconnectedElementException if the generator is disconnected.
        """
        if not self.connected:
            raise DisconnectedElementException(repr(self), Generator.__name__)
        return self._direct_transient_reactance_pu * self._pu_base_reactance

    @property
    def direct_transient_admittance(self) -> complex:
        """
        Return the direct transient admittance.

        :return: Direct transient admittance (per unit).
        """
        return self._direct_transient_admittance if self.connected else 0j

    @property
    def complex_power(self) -> complex:
        """
        Complex power of the generator.

        :return: Complex power of the generator (per unit).
        """
        return self._complex_power if self.connected else 0j

    @property
    def internal_voltage(self) -> complex:
        """
        Internal voltage of the generator

        :return: Phasor corresponding to the internal voltage (per unit).
        """
        if not self.connected:
            # Generator is not connected
            return 0
        return self._internal_voltage

    @property
    def rotor_angle(self) -> float:
        """
        Rotor angle of the generator.
        It is equal to the internal angle in the pre-fault state.

        :return: Rotor angle (radian)
        """
        return self._rotor_angle if self.connected else 0

    @property
    def mechanical_power(self) -> float:
        """
        Mechanical power of the generator.

        :return: Mechanical power
        """
        return self.complex_power.real if self.connected else 0

    @property
    def inertia_coefficient(self) -> float:
        """
        Inertia coefficient of the generator.

        :return: The inertia coefficient.
        """
        return 2 * self._inertia_constant


class DynamicGenerator:
    """
    Generator in a network whose rotor angle can evolve with time.
    """

    def __init__(self, generator: Generator):
        """
        Generate a dynamic generator based on an existing generator.

        :param generator: Generator whose rotor angle will evolve with time.
        """
        from .network import NetworkState
        self._generator = generator
        self._rotor_angles: Dict[float, float] = {0: generator.rotor_angle}
        self._angular_speeds: Dict[float, float] = {0: 0}
        self._network_states: Dict[float, NetworkState] = {0: NetworkState.PRE_FAULT}

    def __repr__(self):
        """
        Representation of a dynamic generator.
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
    def generator(self) -> Generator:
        """
        Get the generator represented by this dynamic generator.

        :return: The represented generator.
        """
        return self._generator

    @property
    def source(self) -> GeneratorSource:
        """
        Get the energy source of the generator.

        :return: The type of energy source.
        """
        return self._generator.source

    @property
    def name(self) -> str:
        """
        Get the generator name.

        :return: The name of the generator.
        """
        return self._generator.name

    @property
    def bus(self) -> 'Bus':
        """
        Return the bus to whih the generator is connected.

        :return: Thus connected bus.
        """
        return self._generator.bus

    @property
    def active_power_pu(self) -> float:
        """
        Return the active power in per unit.
        """
        return self._generator.active_power_pu

    @property
    def max_active_power_pu(self) -> float:
        """
        Return the maximum active power in per unit.
        """
        return self._generator.max_active_power_pu

    @property
    def mechanical_power(self) -> float:
        """
        Mechanical power of the generator.

        :return: Mechanical power
        """
        return self._generator.mechanical_power

    @property
    def observation_times(self) -> List[float]:
        """
        Times at which a rotor angle value was specified.

        :return: Times at which rotor angle values are available.
        """
        return list(self._rotor_angles.keys())

    @property
    def inertia_coefficient(self) -> float:
        """
        Inertia coefficient of the generator.

        :return: The inertia coefficient.
        """
        return self._generator.inertia_coefficient

    def get_rotor_angle(self, time: float) -> float:
        """
        Get the rotor angle of the generator at a specific time.

        :param time: The time for which the angle must be returned.
        :return: Rotor angle (rad) at the expected time.
        :raise: UnknownRotorAngleException if the rotor angle is unknown for the specified time.
        """
        try:
            return self._rotor_angles[time] if self._generator.connected else 0
        except KeyError:
            raise UnknownRotorAngleException(self._generator.name, time)

    def add_rotor_angle(self, time: float, rotor_angle: float):
        """
        Add a rotor angle value at a specific time.

        :param time: Time (s) associated to the rotor angle value.
        :param rotor_angle: Rotor angle (rad) to add.
        """
        self._rotor_angles[time] = rotor_angle

    def add_network_state(self, time: float, state: 'NetworkState'):
        """
        Add state in which the network is at the specified time.
        Allow to specify the state when the angular speed and rotor angle were computed.

        :param time: Time (s) at which the network state must be set.
        :param state: Network state.
        """
        self._network_states[time] = state

    def get_network_state(self, time: float) -> 'NetworkState':
        """
        Get the state in which the network was at the specified time.

        :param time: Time (s) for which the network state must be known.
        :return: The network state at the specified time.
        """
        try:
            return self._network_states[time]
        except KeyError:
            raise UnknownNetworkStateException(self._generator.name, time)

    def get_angular_speed(self, time: float) -> float:
        """
        Get the angular speed of the generator at a specific time.

        :param time: The time for which the speed must be returned.
        :return: Angular speed (p.u.) at the expected time.
        :raise: UnknownAngularSpeedException if the speed is unknown for the specified time.
        """
        try:
            return self._angular_speeds[time] if self._generator.connected else 0
        except KeyError:
            raise UnknownAngularSpeedException(self._generator.name, time)

    def add_angular_speed(self, time: float, angular_speed: float):
        """
        Add an angular speed value at a specific time.

        :param time: Time associated to the speed value.
        :param rotor_angle: Angular speed (p.u.) to add.
        """
        self._angular_speeds[time] = angular_speed

    def delete(self, time: float):
        """
        Delete the data (angle, angular speed and state) a specific time.

        :param time: Target time (s).
        """
        for data_dict in [self._rotor_angles, self._network_states, self._angular_speeds]:
            try:
                data_dict.pop(time)
            except KeyError:
                # No data associated to the specified time
                pass

    def reset(self):
        """
        Reset the generator removing all angle updates.
        """
        from .network import NetworkState
        self._rotor_angles = {0: self.generator.rotor_angle}
        self._angular_speeds = {0: 0}
        self._network_states = {0: NetworkState.PRE_FAULT}
