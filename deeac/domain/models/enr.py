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

class ENRType(Enum):
    PQ = "PQ"
    PV = "PV"

class ENR:
    """
    ENR in a network.
    """

    def __init__(
        self, name: str, type: ENRType, bus: 'Bus', active_power: float, max_active_power: float,
        reactive_power: float, connected: bool = True
    ):
        """
        Initialize an ENR.

        :param name: Name of the generator.
        :param type: Type of generator (PV or PQ).
        :param bus: Bus to which the generator is connected.
        :param active_power: Active power of the generator. Unit: MW.
        :param max_active_power: Maximum active power of the generator. Unit: MW.
        :param reactive_power: Reactive power of the generator. Unit: MVAr.
        :param connected: True if the generator is connected to the network, False otherwise.
        """
        self.name = name
        self.type = type
        self._bus = bus

        self._active_power_pu = active_power / BASE_POWER
        self._max_active_power_pu = max_active_power / BASE_POWER
        self._reactive_power_pu = reactive_power / BASE_POWER

        self.connected = connected

        # Compute properties
        self._complex_power = complex(self._active_power_pu, self._reactive_power_pu)

    def __repr__(self):
        """
        Representation of an ENR.
        """
        return (
            f"ENR: Name=[{self.name}] Type=[{self.type.name}] Bus=[{self._bus.name}] "
            f"P=[{self.active_power}] Pmax=[{self.max_active_power}]  "
            f"Q=[{self.reactive_power}] "
            f"Connected=[{self.connected}]"
        )

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
        return self._max_active_power_pu * BASE_POWER

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
        return self._active_power_pu * BASE_POWER

    @property
    def reactive_power(self) -> float:
        """
        Return the reactive power value.

        :return: The reactive power value in MVAr.
        """
        return self._reactive_power_pu * BASE_POWER

    @property
    def complex_power(self) -> complex:
        """
        Complex power of the generator.

        :return: Complex power of the generator (per unit).
        """
        return self._complex_power if self.connected else 0j
