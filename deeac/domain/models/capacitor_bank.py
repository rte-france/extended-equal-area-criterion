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


class CapacitorBank:
    """
    Capacitor bank in a network.
    """

    def __init__(self, name: str, bus: 'Bus', active_power_pu: float, reactive_power_pu: float):  # TODO
        """
        Initialize a load.

        :param name: Name of the load.
        :param bus: Bus to which the load is connected.
        :param active_power_pu: Active power at the load.
        :param reactive_power_pu: Reactive power at the load.
        """
        self.name = name
        self._bus = bus
        self._active_power_pu = active_power_pu
        self._reactive_power_pu = reactive_power_pu

        # Compute properties
        self.compute_admittance()

    def __repr__(self):
        """
        Representation of a capacitor bank.
        """
        return (
            f"Capacitor bank: Name=[{self.name}] Bus=[{self.bus.name}] P=[{self._active_power}] "
            f"Q=[{self._reactive_power}]"
        )

    def compute_admittance(self):
        """
        Compute the admittance of this capacitor bank.
        """
        bus_voltage_magnitude = self.bus.voltage_magnitude_pu
        if bus_voltage_magnitude == 0j:
            # Admittance is infinite
            self._admittance = complex(np.inf, np.NINF)
            return
        self._admittance = np.conj(self.complex_power) / bus_voltage_magnitude ** 2

    @property
    def complex_power(self) -> complex:
        """
        Complex power of this capacitor bank.

        :return: Complex power
        """
        return complex(self._active_power_pu, self._reactive_power_pu)

    @property
    def admittance(self) -> complex:
        """
        Capacitor bank admittance.

        :return: Phasor representing the capacitor bank admittance.
        """
        return self._admittance

    @property
    def bus(self) -> 'Bus':
        """
        Return the bus to which the capacitor bank is connected.

        :return: The connected bus.
        """
        return self._bus

    @bus.setter
    def bus(self, bus: 'Bus'):
        """
        Change the bus to which the capacitor bank is connected.

        :param bus: The new bus.
        """
        self._bus = bus
        self.compute_admittance()
