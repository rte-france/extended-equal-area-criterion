# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.domain.models import Network, Line
from .mitigation_event import MitigationEvent
from deeac.domain.ports.dtos.events import LineShortCircuitClearingEvent as LineShortCircuitClearingEventDto
from deeac.domain.exceptions import UnexpectedBranchElementException


class LineShortCircuitClearingEvent(MitigationEvent):
    """
    Class that models a line short-circuit clearing.
    """

    def __init__(self, first_bus_name: str, second_bus_name: str, parallel_id: str):
        """
        Initialize the event.

        :param first_bus_name: Name of the first bus connected to the line.
        :param second_bus_name: Name of the second bus connected to the line.
        :param parallel_id: Parallel ID of this line on the branch between the two buses.
        """
        self.first_bus_name = first_bus_name
        self.second_bus_name = second_bus_name
        self.parallel_id = parallel_id

    def __repr__(self):
        """
        Representation of a bus short circuit clearing event.
        """
        return (
            f"Line short-circuit clearing event: Branch=[{self.first_bus_name}, {self.second_bus_name}] "
            f"Parallel ID=[{self.parallel_id}]"
        )

    @classmethod
    def create_event(cls, event_data: LineShortCircuitClearingEventDto) -> 'LineShortCircuitClearingEvent':
        """
        Create a clearing event based on input event data.

        :param event_data: The event data.
        :return: A line short-circuit clearing event based on the event data.
        """
        return cls(
            first_bus_name=event_data.first_bus_name,
            second_bus_name=event_data.second_bus_name,
            parallel_id=event_data.parallel_id
        )

    def apply_to_network(self, network: Network):
        """
        Apply the event to the network given as argument.
        This method modifies the network given as argument according to the event.

        :param network: The network to which the event must be applied.
        :raise ParallelException if no element is at the specified parallel ID on the branch.
        :raise ElementNotFoundException if no breaker can be found between the two buses in the network.
        :raise UnexpectedBranchElementException if element at the specified parallel ID is not a line.
        """
        # Get line
        first_bus_name = self.first_bus_name
        second_bus_name = self.second_bus_name
        branch = network.get_branch(first_bus_name, second_bus_name)
        line = branch[self.parallel_id]
        if type(line) != Line:
            raise UnexpectedBranchElementException(
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
