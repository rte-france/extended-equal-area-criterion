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
from deeac.domain.ports.dtos.events import BreakerEvent as BreakerEventDto


class BreakerEvent(MitigationEvent):
    """
    Class that models a breaker opening or closing.
    """

    def __init__(self, first_bus_name: str, second_bus_name: str, parallel_id: str, breaker_closed: bool):
        """
        Initialize the event.

        :param first_bus_name: Name of the first bus connected to the breaker.
        :param second_bus_name: Name of the second bus connected to the breaker.
        :param parallel_id: Parallel ID of this breaker on the branch.
        :param breaker_closed: Determine if the breaker must be closed.
        """
        self.first_bus_name = first_bus_name
        self.second_bus_name = second_bus_name
        self.parallel_id = parallel_id
        self.breaker_closed = breaker_closed

    def __repr__(self):
        """
        Representation of a breaker event.
        """
        return (
            f"Breaker event: Buses=[{self.first_bus_name}, {self.second_bus_name}] "
            f"Parallel ID=[{self.parallel_id}] Breaker closed=[{self.breaker_closed}]"
        )

    @classmethod
    def create_event(cls, event_data: BreakerEventDto) -> 'BreakerEvent':
        """
        Create a breaker event based on input event data.

        :param event_data: The event data.
        :return: A breaker event based on the event data.
        """
        return cls(
            first_bus_name=event_data.first_bus_name,
            second_bus_name=event_data.second_bus_name,
            parallel_id=event_data.parallel_id,
            breaker_closed=event_data.breaker_closed
        )

    def apply_to_network(self, network: Network):
        """
        Apply the event to the network given as argument.
        This method modifies the network given as argument according to the event.

        :param network: The network to which the event must be applied.
        :raise ElementNotFoundException if no breaker can be found between the two buses in the network.
        :raise ParallelException if no element is at the specified parallel ID on the branch.
        """
        # Update breaker state
        network.change_breaker_position(
            self.first_bus_name, self.second_bus_name, self.parallel_id, self.breaker_closed
        )
