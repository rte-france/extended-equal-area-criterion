"""
Module for line_short_circuit_clearing_event.

:module: line_short_circuit_clearing_event
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.Models.line import Line
from deeac.Models.network import Network
from deeac.Models.events.mitigation_event import MitigationEvent


class LineShortCircuitClearingEvent(MitigationEvent):
    """
    Lineshortcircuitclearingevent.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar time: time.
    :ivar first_bus_name: first bus name.
    :ivar second_bus_name: second bus name.
    :ivar parallel_id: parallel id.
    """

    def __init__(self, time: float, first_bus_name: str, second_bus_name: str, parallel_id: str):
        """
        Initialize the event.
        
        :param first_bus_name: Name of the first bus connected to the line.
        :param second_bus_name: Name of the second bus connected to the line.
        :param parallel_id: Parallel ID of this line on the branch between the two buses.
        """
        self.time = time
        self.first_bus_name = first_bus_name
        self.second_bus_name = second_bus_name
        self.parallel_id = parallel_id

    def __repr__(self):
        """
        repr  .
        
        :return: Return value.
        """
        return (
            f"Line short-circuit clearing event: Branch=[{self.first_bus_name}, {self.second_bus_name}] "
            f"Parallel ID=[{self.parallel_id}]"
        )

    def apply_to_network(self, network: Network):
        """
        Apply the event to the network given as argument.
        This method modifies the network given as argument according to the event.
        
        :param network: The network to which the event must be applied.
        """
        # Get line
        first_bus_name = self.first_bus_name
        second_bus_name = self.second_bus_name
        branch = network.get_branch(first_bus_name, second_bus_name)
        line = branch[self.parallel_id]
        if type(line) != Line:
            raise TypeError(
                first_bus_name, second_bus_name, self.parallel_id, type(line), Line.__name__
            )

        # Check if event bus order is same as branch bus order
        if branch.first_bus.name != self.first_bus_name:
            first_bus = branch.second_bus
            second_bus = branch.first_bus
        else:
            first_bus = branch.first_bus
            second_bus = branch.second_bus

        # Remove fictive loads
        first_load_name = f"FICT_LOAD_{self.parallel_id}_{second_bus.name}_{first_bus.name}"
        second_load_name = f"FICT_LOAD_{self.parallel_id}_{first_bus.name}_{second_bus.name}"
        first_bus.loads = set(load for load in first_bus.loads if load.name != first_load_name)
        second_bus.loads = set(load for load in second_bus.loads if load.name != second_load_name)
        line.metal_short_circuited = False


    pass


def create_line_short_circuit_clearing_event(event_data: dict) -> LineShortCircuitClearingEvent:
    """
    Create a clearing event based on input event data.
    
    :param event_data: The event data.
    :return: A line short-circuit clearing event based on the event data.
    """
    return LineShortCircuitClearingEvent(
        time=event_data['time'],
        first_bus_name=event_data['first_bus_name'],
        second_bus_name=event_data['second_bus_name'],
        parallel_id=event_data['parallel_id']
    )


def parse_line_short_circuit_clearing_from_eurostag(event_data: dict) -> LineShortCircuitClearingEvent:
    """
    Parse a clearing event from Eurostag data.
    
    :param event_data: Dictionary with the event data from eurostag file.
    :return: Parsed LineShortCircuitClearingEvent.
    """
    return LineShortCircuitClearingEvent(
        time=float(event_data['time']),
        first_bus_name=event_data['sending_node'],
        second_bus_name=event_data['receiving_node'],
        parallel_id=event_data['parallel_index'],
    )
