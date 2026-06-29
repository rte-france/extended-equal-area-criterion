"""
Module for branch_event.

:module: branch_event
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.enums import BreakerPosition
from deeac.Models.network import Network
from deeac.Models.events.mitigation_event import MitigationEvent


class BranchEvent(MitigationEvent):
    """
    Branchevent.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar time: time.
    :ivar first_bus_name: first bus name.
    :ivar second_bus_name: second bus name.
    :ivar parallel_id: parallel id.
    :ivar breaker_position: breaker position.
    :ivar breaker_closed: breaker closed.
    """

    def __init__(
        self, time: float, first_bus_name: str, second_bus_name: str, parallel_id: str, breaker_position: BreakerPosition,
        breaker_closed: bool = False
    ):
        """
        Initialize the event.
        
        :param first_bus_name: Name of the first bus connected to the line.
        :param second_bus_name: Name of the second bus connected to the line.
        :param parallel_id: Parallel ID of this line on the branch between the two buses.
        :param breaker_position: Determine at which bus connected to the line the breaker is opened or closed.
        :param breaker_closed: Defines if the breaker is closed.
        """
        self.time = time
        self.first_bus_name = first_bus_name
        self.second_bus_name = second_bus_name
        self.parallel_id = parallel_id
        self.breaker_position = breaker_position
        self.breaker_closed = breaker_closed

    def __repr__(self):
        """
        repr  .
        
        :return: Return value.
        """
        return (
            f"Branch event: Branch=[{self.first_bus_name}, {self.second_bus_name}] "
            f"Parallel ID=[{self.parallel_id}] Breaker position=[{self.breaker_position.value}] "
            f"Breaker closed=[{self.breaker_closed}]"
        )

    def apply_to_network(self, network: Network):
        """
        Apply the event to the network given as argument.
        This method modifies the network given as argument according to the event.
        
        :param network: The network to which the event must be applied.
        """
        # Get branch
        first_bus_name = self.first_bus_name
        second_bus_name = self.second_bus_name
        branch = network.get_branch(first_bus_name, second_bus_name)
        # Check if branch buses correspond to order in the event
        breaker_position = self.breaker_position
        if branch.first_bus.name != self.first_bus_name:
            # Invert breaker position
            breaker_position = (
                BreakerPosition.FIRST_BUS if breaker_position == BreakerPosition.SECOND_BUS else
                BreakerPosition.SECOND_BUS
            )
            first_bus_name = second_bus_name
            second_bus_name = self.first_bus_name

        element = branch[self.parallel_id]
        if not self.breaker_closed:
            # Breaker is opened, remove the fictive loads
            if breaker_position == BreakerPosition.FIRST_BUS:
                fictive_load_name = f"FICT_LOAD_{self.parallel_id}_{second_bus_name}_{first_bus_name}"
                bus = branch.first_bus
                element.closed_at_first_bus = False
            else:
                fictive_load_name = f"FICT_LOAD_{self.parallel_id}_{first_bus_name}_{second_bus_name}"
                bus = branch.second_bus
                element.closed_at_second_bus = False
            # Remove loads from line short circuit
            bus.loads = set(load for load in bus.loads if load.name != fictive_load_name)
            return True
        else:
            raise NotImplementedError("Event to close a line or TFO is not implemented yet.")


    pass


