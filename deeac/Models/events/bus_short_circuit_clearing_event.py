"""
Module for bus_short_circuit_clearing_event.

:module: bus_short_circuit_clearing_event
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.Models.network import Network
from deeac.Models.events.mitigation_event import MitigationEvent


class BusShortCircuitClearingEvent(MitigationEvent):
    """
    Busshortcircuitclearingevent.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar time: time.
    :ivar bus_name: bus name.
    """

    def __init__(self, time:float, bus_name: str):
        """
        Initialize the event.
        
        :param bus_name: Name of the bus where the short circuit happened.
        """
        self.time = time
        self.bus_name = bus_name

    def __repr__(self):
        """
        repr  .
        
        :return: Return value.
        """
        return f"Bus short-circuit clearing event: Bus=[{self.bus_name}]"

    def apply_to_network(self, network: Network):
        """
        Apply the event to the network given as argument.
        This method modifies the network given as argument according to the event.
        
        :param network: The network to which the event must be applied.
        """
        # Get bus on which the fault occurs
        bus = network.get_bus(self.bus_name)

        # Remove fictive load
        load_name = f"FICT_LOAD_{bus.name}"
        bus.loads = set(load for load in bus.loads if load.name != load_name)

    pass


def create_bus_short_circuit_clearing_event(event_data: dict) -> BusShortCircuitClearingEvent:
    """
    Create a clearing event based on input event data.
    
    :param event_data: The event data.
    :return: A bus short circuit clearing event based on the event data.
    """
    return BusShortCircuitClearingEvent(time=event_data['time'], bus_name=event_data['bus_name'])


def parse_bus_short_circuit_clearing_from_eurostag(event_data: dict) -> BusShortCircuitClearingEvent:
    """
    Parse a clearing event from Eurostag data.
    
    :param event_data: Dictionary with the event data from eurostag file.
    :return: Parsed BusShortCircuitClearingEvent.
    """
    return BusShortCircuitClearingEvent(time=float(event_data['time']), bus_name=event_data['node'])
