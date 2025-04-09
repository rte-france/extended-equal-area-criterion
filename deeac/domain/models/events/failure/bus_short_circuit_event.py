# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import sys

from deeac.domain.models import Network, Bus, FictiveLoad, Value, Unit
from deeac.domain.ports.dtos.events import BusShortCircuitEvent as BusShortCircuitEventDto
from .failure_event import FailureEvent


class BusShortCircuitEvent(FailureEvent):
    """
    Class that models a short circuit on a bus.
    """

    def __init__(
        self, bus_name: str, fault_resistance: float = 0, fault_reactance: float = 0
    ):
        """
        Initialize the event.

        :param bus_name: Name of the bus where the short circuit happens.
        :param fault_resistance: Resistance associated to the fault in case of impedance fault.
        :param fault_reactance: Reactance associated to the fault in case of impedance fault.
        """
        self.bus_name = bus_name
        # Use epsilon for impedance to avoid infinite values in computations
        if fault_resistance == 0:
            fault_resistance = sys.float_info.epsilon
        self.fault_resistance = fault_resistance
        self.fault_reactance = fault_reactance

    def __repr__(self):
        """
        Representation of a bus short circuit.
        """
        return (
            f"Bus short circuit: Bus=[{self.bus_name}] R=[{self.fault_resistance}] X=[{self.fault_reactance}]"
        )

    @classmethod
    def create_event(cls, event_data: BusShortCircuitEventDto) -> 'BusShortCircuitEvent':
        """
        Create a bus short circuit event based on input event data.

        :param event_data: The event data.
        :return: A bus short circuit event based on the event data.
        """
        return cls(
            bus_name=event_data.bus_name,
            fault_resistance=Value.from_dto(event_data.fault_resistance).to_unit(Unit.OHM),
            fault_reactance=Value.from_dto(event_data.fault_reactance).to_unit(Unit.OHM),
        )

    def apply_to_network(self, network: Network):
        """
        Apply the event to the network given as argument.
        This method modifies the network given as argument according to the event.

        :param network: The network to which the event must be applied.
        """
        # Get bus on which the fault occurs
        bus = network.get_bus(self.bus_name)

        # Compute admittance
        admittance = 1 / complex(self.fault_resistance.to_unit(Unit.OHM), self.fault_reactance.to_unit(Unit.OHM))

        # Add fictive load
        bus.add_load(FictiveLoad(
            name=f"FICT_LOAD_{bus.name}",
            bus=bus,
            admittance=admittance)
        )

        return True


    def get_nearest_bus(self, network: Network) -> Bus:
        """
        Get the bus that is the nearest to the fault.

        :param network: Network in which the bus must be found.
        :return: The nearest bus to the fault.
        """
        return network.get_bus(self.bus_name)
