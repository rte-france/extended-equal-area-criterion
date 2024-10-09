# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.domain.models import Network
from .mitigation_event import MitigationEvent
from deeac.domain.ports.dtos.events import BusShortCircuitClearingEvent as BusShortCircuitClearingEventDto


class BusShortCircuitClearingEvent(MitigationEvent):
    """
    Class that models a bus short-circuit clearing.
    """

    def __init__(self, bus_name: str):
        """
        Initialize the event.

        :param bus_name: Name of the bus where the short circuit happened.
        """
        self.bus_name = bus_name

    def __repr__(self):
        """
        Representation of a bus short circuit clearing event.
        """
        return f"Bus short-circuit clearing event: Bus=[{self.bus_name}]"

    @classmethod
    def create_event(cls, event_data: BusShortCircuitClearingEventDto) -> 'BusShortCircuitClearingEvent':
        """
        Create a clearing event based on input event data.

        :param event_data: The event data.
        :return: A bus short circuit clearing event based on the event data.
        """
        return cls(bus_name=event_data.bus_name)

    def apply_to_network(self, network: Network):
        """
        Apply the event to the network given as argument.
        This method modifies the network given as argument according to the event.

        :param network: The network to which the event must be applied.
        :raise ElementNotFoundException if no breaker can be found between the two buses in the network.
        """
        # Get bus on which the fault occurs
        bus = network.get_bus(self.bus_name)

        # Remove fictive load
        load_name = f"FICT_LOAD_{bus.name}"
        bus.loads = [load for load in bus.loads if load.name != load_name]
