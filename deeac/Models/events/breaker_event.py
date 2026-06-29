"""
Module for breaker_event.

:module: breaker_event
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.
from typing import Union

from deeac.Models.network import Network
from deeac.Models.events.mitigation_event import MitigationEvent
from deeac.Models.events.branch_event import BranchEvent, BreakerPosition


class BreakerEvent(MitigationEvent):
    """
    Class that models a breaker opening or closing.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar time: Time in seconds.
    :ivar first_bus_name: Name of first bus.
    :ivar second_bus_name: Name of second bus.
    :ivar parallel_id: Identifier for parallel.
    :ivar breaker_closed: Value for breaker closed.
    """

    def __init__(self, time: float, first_bus_name: str, second_bus_name: str, parallel_id: str, breaker_closed: bool):
        """
        Initialize the event.
        
        :param first_bus_name: Name of the first bus connected to the breaker.
        :param second_bus_name: Name of the second bus connected to the breaker.
        :param parallel_id: Parallel ID of this breaker on the branch.
        :param breaker_closed: Determine if the breaker must be closed.
        """
        self.time = time
        self.first_bus_name = first_bus_name
        self.second_bus_name = second_bus_name
        self.parallel_id = parallel_id
        self.breaker_closed = breaker_closed

    def __repr__(self):
        """
        Representation of a breaker event.
        
        :return: Return value.
        """
        return (
            f"Breaker event: Buses=[{self.first_bus_name}, {self.second_bus_name}] "
            f"Parallel ID=[{self.parallel_id}] Breaker closed=[{self.breaker_closed}]"
        )

    def apply_to_network(self, network: Network):
        """
        Apply the event to the network given as argument.
        This method modifies the network given as argument according to the event.
        
        :param network: The network to which the event must be applied.
        """
        # Update breaker state
        network.change_breaker_position(
            self.first_bus_name, self.second_bus_name, self.parallel_id, self.breaker_closed
        )
        return True


class BreakerOpeningEvent(BreakerEvent):
    """
    BreakerOpeningEvent container.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :summary: Class metadata.
    """
    pass


class BreakerClosingEvent(BreakerEvent):
    """
    BreakerClosingEvent container.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :summary: Class metadata.
    """
    pass


def create_breaker_event(event_data: dict) -> BreakerEvent:
    """
    Create a breaker event based on input event data.
    
    :param event_data: The event data.
    :return: A breaker event based on the event data.
    """
    return BreakerEvent(
        time=event_data['time'],
        first_bus_name=event_data['first_bus_name'],
        second_bus_name=event_data['second_bus_name'],
        parallel_id=event_data['parallel_id'],
        breaker_closed=event_data['breaker_closed']
    )


def parse_breaker_opening_from_eurostag(event_data: dict) -> Union[BreakerEvent, BranchEvent]:
    """
    Parse a breaker opening event from Eurostag data.
    
    :param event_data: Event data.
    :return: BreakerEvent or BranchEvent.
    """
    if event_data.get('branch_type', None) is None:
        if event_data['position'] == 'S':
            position = BreakerPosition.FIRST_BUS
        else:
            position = BreakerPosition.SECOND_BUS

        return BranchEvent(
            time=float(event_data['time']),
            first_bus_name=event_data['sending_node'],
            second_bus_name=event_data['receiving_node'],
            parallel_id=event_data['parallel_index'],
            breaker_position=position,
            breaker_closed=False
        )

    if event_data.get('branch_type', None) == '2':
        return BreakerEvent(
            time=float(event_data['time']),
            first_bus_name=event_data['first_coupled_node'],
            second_bus_name=event_data['second_coupled_node'],
            parallel_id=event_data['coupling_index'],
            breaker_closed=False
        )

    raise NotImplementedError(
        f"[Event parser] Opening/closing an element of type {event_data['branch_type']} "
        f"is not supported."
    )


def parse_breaker_closing_from_eurostag(event_data: dict) -> Union[BreakerEvent, BranchEvent]:
    """
    Parse a breaker closing event from Eurostag data.
    
    :param event_data: Event data.
    :return: BreakerEvent or BranchEvent.
    """
    if event_data.get('branch_type', None) is None:
        return BranchEvent(
            time=event_data['time'],
            first_bus_name=event_data['sending_node'],
            second_bus_name=event_data['receiving_node'],
            parallel_id=event_data['parallel_index'],
            breaker_position=event_data['position'],
            breaker_closed=True
        )

    if event_data.get('branch_type', None) == '2':
        return BreakerEvent(
            time=event_data['time'],
            first_bus_name=event_data['first_coupled_node'],
            second_bus_name=event_data['second_coupled_node'],
            parallel_id=event_data['coupling_index'],
            breaker_closed=True
        )

    raise NotImplementedError(
        f"[Event parser] Opening/closing an element of type {event_data['branch_type']} "
        f"is not supported."
    )

