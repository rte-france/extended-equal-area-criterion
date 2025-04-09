# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from .bus import Bus


class Load:
    """
    Load in a network.
    """

    def __init__(self, name: str, bus: 'Bus', base_power: float,
                 active_power: float, reactive_power: float, connected: bool = True):
        """
        Initialize a load.

        :param name: Name of the load.
        :param bus: Bus to which the load is connected.
        :param active_power: Active power at the load. Unit: MW.
        :param reactive_power: Reactive power at the load. unit: MVAr.
        :param connected: True if the load is connected to the network, False othetwise.
        """
        self.name = name
        self._bus = bus
        self._base_power = base_power
        self._active_power_pu = active_power / base_power
        self._reactive_power_pu = reactive_power / base_power
        self.connected = connected

        # Compute properties
        self.compute_admittance()

    def __repr__(self):
        """
        Representation of a load.
        """
        return (
            f"Load: Name=[{self.name}] Bus=[{self.bus.name}] P=[{self.active_power}] Q=[{self.reactive_power}] "
            f"Connected=[{self.connected}]"
        )

    def compute_admittance(self):
        """
        Compute the admittance of this load.
        """
        if self.bus.voltage == 0:
            # Bus not connected to the network.
            self._admittance = 0j
        else:
            self._admittance = np.conj(self.complex_power_pu) / self.bus.voltage_magnitude_pu ** 2

    @property
    def active_power(self) -> float:
        """
        Return the active power value.

        :return: The active power in MW.
        """
        return self._active_power_pu * self._base_power

    @property
    def reactive_power(self) -> float:
        """
        Return the active power value.

        :return: The active power in MW.
        """
        return self._reactive_power_pu * self._base_power

    @property
    def complex_power_pu(self) -> complex:
        """
        Complex power of this load.

        :return: Complex power
        """
        return complex(self._active_power_pu, self._reactive_power_pu) if self.connected else 0j

    @property
    def admittance(self) -> complex:
        """
        Load admittance.

        :return: Phasor representing the load admittance.
        """
        return self._admittance if self.connected else 0j

    @property
    def bus(self) -> 'Bus':
        """
        Return the bus to which the load is connected.

        :return: The connected bus.
        """
        return self._bus

    @bus.setter
    def bus(self, bus: 'Bus'):
        """
        Change the bus to which the load is connected.
        """
        self._bus = bus
        self.compute_admittance()


class FictiveLoad(Load):
    """
    Fictive load with a specific admittance used to model a fault on a line or a bus.
    This kind of load is associated to active and reactive powers equal to 0.
    """
    def __init__(self, name: str, bus: 'Bus', base_power: float, admittance: complex, connected: bool = True):
        """
        Initialize a load.

        :param name: Name of the load.
        :param bus: Bus to which the load is connected.
        :param admittance: Admittance of this load (S).
        :param connected: True if the load is connected to the network, False othetwise.
        """
        super().__init__(
            name=name,
            bus=bus,
            base_power=base_power,
            active_power=0,
            reactive_power=0,
            connected=connected
        )
        self._admittance = admittance

    def __repr__(self):
        """
        Representation of a fictive load.
        """
        return (
            f"Fictive load: Name=[{self.name}] Bus=[{self.bus.name}] Y=[{self._admittance} S] "
            f"Connected=[{self.connected}]"
        )

    def compute_admittance(self):
        """
        Compute the admittance of this load.
        """
        # The admittance of a fictive load is constant.
        return

    @property
    def complex_power(self) -> complex:
        """
        Complex power of this fictive load.

        :return: Complex power
        """
        return 0j
