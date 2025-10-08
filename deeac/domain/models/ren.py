# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import TYPE_CHECKING
from enum import Enum
if TYPE_CHECKING:
    from .bus import Bus
from deeac.domain.models.constants import BASE_POWER

class RENType(Enum):
    PQ = "PQ"
    PV = "PV"

class REN:
    """
    REN in a network.
    """

    def __init__(
        self, name: str, type: RENType, bus: 'Bus', active_power: float, max_active_power: float,
        reactive_power: float, connected: bool = True
    ):
        """
        Initialize a REN.

        :param name: Name of the REN.
        :param type: Type of measure (PV or PQ).
        :param bus: Bus to which the REN is connected.
        :param active_power: Active power of the REN. Unit: MW.
        :param max_active_power: Maximum active power of the REN. Unit: MW.
        :param reactive_power: Reactive power of the REN. Unit: MVAr.
        :param connected: True if the REN is connected to the network, False otherwise.
        """
        self.name = name
        self.type = type
        self._bus = bus

        self.active_power = active_power
        self._active_power_pu = active_power / BASE_POWER
        self.max_active_power = max_active_power
        self._max_active_power_pu = max_active_power / BASE_POWER
        self.reactive_power = reactive_power
        self._reactive_power_pu = reactive_power / BASE_POWER

        self.connected = connected
        if bus.voltage!=0:
            self.current = (active_power - 1j * reactive_power) / bus.voltage.conjugate()
        else:
            self.current = 0

        # Compute properties
        self._complex_power = complex(self._active_power_pu, self._reactive_power_pu)

    def __repr__(self):
        """
        Representation of a REN.
        """
        return (
            f"REN: Name=[{self.name}] Type=[{self.type.name}] Bus=[{self._bus.name}] "
            f"P=[{self.active_power}] Pmax=[{self.max_active_power}]  "
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
    def max_active_power_pu(self) -> float:
        """
        Return the maximum active power in per unit.
        """
        return self._max_active_power_pu

    @property
    def active_power_pu(self) -> float:
        """
        Return the active power in per unit.
        """
        return self._active_power_pu

    @property
    def complex_power(self) -> complex:
        """
        Complex power of the REN.

        :return: Complex power of the REN (per unit).
        """
        return self._complex_power if self.connected else 0j
