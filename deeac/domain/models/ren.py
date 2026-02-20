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
    from .bus import Bus
from deeac.domain.models.constants import BASE_POWER
import numpy as np

class REN:
    """
    REN in a network.
    """

    def __init__(
        self, name: str, bus: 'Bus', active_power: float, reactive_power: float, model: str, connected: bool = True
    ):
        """
        Initialize a REN.

        :param name: Name of the REN.
        :param bus: Bus to which the REN is connected.
        :param active_power: Active power of the REN. Unit: MW.
        :param reactive_power: Reactive power of the REN. Unit: MVAr.
        :param model: REN model (load or current_source).
        :param connected: True if the REN is connected to the network, False otherwise.
        """
        self.name = name
        self.model = model
        self._bus = bus

        self.active_power = active_power
        self._active_power_pu = active_power / BASE_POWER
        self.reactive_power = reactive_power
        self._reactive_power_pu = reactive_power / BASE_POWER

        self.connected = connected
        if bus.voltage!=0:
            self.current = (self._active_power_pu - 1j * self._reactive_power_pu) / bus.voltage.conjugate()
        else:
            self.current = 0j

        # Compute properties
        self._complex_power_pu = complex(self._active_power_pu, self._reactive_power_pu)
        if self.model == "load":
            if self.bus.voltage_magnitude_pu!=0:
                self.admittance = np.conj(self._complex_power_pu) / self.bus.voltage_magnitude_pu ** 2
            else:
                self.admittance = 0j

    def __repr__(self):
        """
        Representation of a REN.
        """
        return (
            f"REN: Name=[{self.name}] Bus=[{self._bus.name}] "
            f"P=[{self.active_power}] "
            f"Q=[{self.reactive_power}] "
            f"Connected=[{self.connected}]"
        )

    @property
    def bus(self) -> 'Bus':
        """
        Return the bus to the REN it is connected with

        :return: Thus connected bus.
        """
        return self._bus

    @bus.setter
    def bus(self, bus: 'Bus'):
        """
        Change the bus connected to the REN.

        :param bus: The new bus to which the REN is connected.
        """
        self._bus = bus

    @property
    def active_power_pu(self) -> float:
        """
        Return the active power in per unit.
        """
        return self._active_power_pu

    @property
    def complex_power_pu(self) -> complex:
        """
        Complex power of the REN.

        :return: Complex power of the REN (per unit).
        """
        return self._complex_power_pu if self.connected else 0j
