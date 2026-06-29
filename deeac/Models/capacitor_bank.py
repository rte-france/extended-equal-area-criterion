"""
Module for capacitor_bank.

:module: capacitor_bank
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
import numpy as np

if TYPE_CHECKING:
    from deeac.Models.bus import Bus

from deeac.Models.constants import BASE_POWER


class CapacitorBank:
    """
    Capacitorbank.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar name: name.
    :ivar bus: bus.
    :ivar active_power: active power.
    :ivar reactive_power: reactive power.
    :ivar connected: connected.
    """

    def __init__(self, name: str, bus: 'Bus',
                 active_power: float, reactive_power: float,
                 connected: bool = True,):
        """
        Initialize a load.
        
        :param name: Name of the load.
        :param bus: Bus to which the load is connected.
        :param active_power: Active power at the load. Unit: MW.
        :param reactive_power: Reactive power at the load. Unit: MVAr.
        """
        self.name = name
        self._bus = bus
        self._connected = connected
        self._active_power_pu = active_power / BASE_POWER
        self._reactive_power_pu = reactive_power / BASE_POWER
        self._admittance = complex(0.0, 0.0)
        # Compute properties
        self.compute_admittance()

    def __repr__(self):
        """
        repr  .
        
        :return: Return value.
        """
        return (
            f"Capacitor bank: Name=[{self.name}] Bus=[{self.bus.name}] P=[{self.active_power}] "
            f"Q=[{self.reactive_power}]"
        )

    def compute_admittance(self):
        """
        Compute admittance.
        
        :return: Result value.
        """
        bus_voltage_magnitude = self.bus.voltage_magnitude_pu
        if bus_voltage_magnitude == 0j:
            # Admittance is infinite
            self._admittance = complex(np.inf, -np.inf)
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

    @property
    def active_power(self) -> float:
        """
        Return the active power value.
        
        :return: The active power in MW.
        """
        return self._active_power_pu * BASE_POWER

    @property
    def reactive_power(self) -> float:
        """
        Return the active power value.
        
        :return: The active power in MW.
        """
        return self._reactive_power_pu * BASE_POWER

    @reactive_power.setter
    def reactive_power(self, reactive_power: float):
        """
        Reactive power.
        
        :param reactive_power: reactive power.
        """
        self._reactive_power_pu = reactive_power / BASE_POWER
        self.compute_admittance()

    @property
    def connected(self) -> bool:
        """
        Return whether the capacitor bank is connected.
        
        :return: True if connected, False otherwise.
        """
        return self._connected
