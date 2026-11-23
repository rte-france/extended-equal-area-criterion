"""
Shared electrical injection state for generator-like network objects.

:module: _generator_injection
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

from deeac.Models.constants import BASE_POWER
from deeac.enums import GeneratorType, GeneratorSource


class GeneratorInjectionParent:
    """
    Shared electrical injection state for synchronous and converter-based units.
    """

    __slots__ = (
        "name",
        "tpe",
        "_bus",
        "_active_power_pu",
        "_max_active_power_pu",
        "_reactive_power_pu",
        "connected",
        "source",
        "regulating",
        "_complex_power",
    )

    def __init__(
            self,
            name: str,
            tpe: GeneratorType,
            bus: "Bus",
            active_power: float,
            max_active_power: float,
            reactive_power: float,
            connected: bool = True,
            source: GeneratorSource = None,
            regulating: bool = False,
    ) -> None:
        """
        Initialize the shared injection state.

        :param name: Generator name.
        :param tpe: Generator operating type.
        :param bus: Connected bus.
        :param active_power: Active power in MW.
        :param max_active_power: Maximum active power in MW.
        :param reactive_power: Reactive power in MVAr.
        :param connected: Connection state.
        :param source: Primary technology/source.
        :param regulating: Voltage-regulating flag.
        :return: Return value.
        """
        # OMIB rationale:
        # Every generator-like object starts as an electrical power injection
        # attached to a bus. Before we decide whether the object belongs to the
        # synchronous-machine dynamic world or to the static converter world,
        # we need the common injection quantities:
        # - bus location
        # - P and Q
        # - connection state
        # - technology/source metadata
        #
        # In OMIB terms, this class is the lowest common denominator shared by
        # all generation objects that modify the electrical network seen by the
        # synchronous machines.
        self.name = name
        self.tpe = tpe
        self._bus = bus
        # OMIB works on per-unit quantities. Converting here guarantees that
        # both synchronous and converter-based objects feed the reduced-network
        # and electrical-power calculations on the same base.
        self._active_power_pu = active_power / BASE_POWER
        self._max_active_power_pu = max_active_power / BASE_POWER
        self._reactive_power_pu = reactive_power / BASE_POWER
        self.connected = connected
        self.source = source
        self.regulating = regulating
        # The complex power is the compact form used downstream by both:
        # - synchronous internal-voltage calculations
        # - converter current/admittance calculations
        self._complex_power = complex(self._active_power_pu, self._reactive_power_pu)

    @property
    def bus(self) -> "Bus":
        """
        Return the connected bus.

        :return: Connected bus.
        """
        return self._bus

    @bus.setter
    def bus(self, bus: "Bus") -> None:
        """
        Change the connected bus.

        :param bus: New connected bus.
        :return: Return value.
        """
        # OMIB rationale:
        # Bus changes matter because OMIB never works on isolated generator
        # attributes only. It always reasons on generators through the network
        # they are connected to. Any subclass-specific electrical state derived
        # from the bus voltage must therefore be refreshed immediately.
        self._bus = bus
        self._on_bus_updated()

    def _on_bus_updated(self) -> None:
        """
        Hook for subclasses that depend on bus voltage.

        :return: Return value.
        """
        # This hook exists because the OMIB world splits into two physical
        # interpretations:
        # - synchronous machines recompute an internal EMF behind reactance
        # - converter-based units recompute a static current/admittance view
        return None

    @property
    def max_active_power_pu(self) -> float:
        """
        Max active power in per unit.

        :return: Max active power in per unit.
        """
        return self._max_active_power_pu

    @property
    def max_active_power(self) -> float:
        """
        Max active power in MW.

        :return: Max active power in MW.
        """
        return self._max_active_power_pu * BASE_POWER

    @max_active_power.setter
    def max_active_power(self, max_active_power: float) -> None:
        """
        Update the maximum active power in MW.

        :param max_active_power: Maximum active power in MW.
        :return: Return value.
        """
        self._max_active_power_pu = max_active_power / BASE_POWER

    @property
    def active_power_pu(self) -> float:
        """
        Active power in per unit.

        :return: Active power in per unit.
        """
        return self._active_power_pu

    @property
    def active_power(self) -> float:
        """
        Active power in MW.

        :return: Active power in MW.
        """
        return self._active_power_pu * BASE_POWER

    @active_power.setter
    def active_power(self, active_power: float) -> None:
        """
        Update the active power in MW.

        :param active_power: Active power in MW.
        :return: Return value.
        """
        # OMIB rationale:
        # P/Q updates change the electrical coupling between the generator side
        # and the reduced network. Subclasses therefore refresh their derived
        # representation after the shared complex power is rebuilt.
        self._active_power_pu = active_power / BASE_POWER
        self._complex_power = complex(self._active_power_pu, self._reactive_power_pu)
        self._on_power_updated()

    @property
    def reactive_power(self) -> float:
        """
        Reactive power in MVAr.

        :return: Reactive power in MVAr.
        """
        return self._reactive_power_pu * BASE_POWER

    @reactive_power.setter
    def reactive_power(self, reactive_power: float) -> None:
        """
        Update the reactive power in MVAr.

        :param reactive_power: Reactive power in MVAr.
        :return: Return value.
        """
        # Same OMIB reasoning as for active power:
        # the electrical side of the machine/source must stay consistent with
        # the latest P/Q injection before any reduced-network computation runs.
        self._reactive_power_pu = reactive_power / BASE_POWER
        self._complex_power = complex(self._active_power_pu, self._reactive_power_pu)
        self._on_power_updated()

    def _on_power_updated(self) -> None:
        """
        Hook for subclasses that derive additional values from P/Q.

        :return: Return value.
        """
        # Subclasses specialize this because the OMIB world does not consume
        # raw P/Q directly. It consumes:
        # - internal voltage for synchronous machines
        # - static current/admittance for converter-based sources
        return None

    @property
    def complex_power(self) -> complex:
        """
        Complex power in per unit.

        :return: Complex power in per unit.
        """
        return self._complex_power if self.connected else 0j
