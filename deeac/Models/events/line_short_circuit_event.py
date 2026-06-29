"""
Module for line_short_circuit_event.

:module: line_short_circuit_event
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.Models.bus import Bus
from deeac.Models.line import Line
from deeac.Models.load import FictiveLoad
from deeac.Models.network import Network
from deeac.Models.events.failure_event import FailureEvent


class LineShortCircuitEvent(FailureEvent):
    """
    Lineshortcircuitevent.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar time: time.
    :ivar first_bus_name: first bus name.
    :ivar second_bus_name: second bus name.
    :ivar parallel_id: parallel id.
    :ivar fault_position: fault position.
    :ivar fault_resistance: fault resistance.
    :ivar fault_reactance: fault reactance.
    """

    def __init__(
        self, time: float, first_bus_name: str, second_bus_name: str, parallel_id: str, fault_position: float,
        fault_resistance: float= 0.0, fault_reactance: float = 0.0
    ):
        """
        Initialize the event.
        
        :param first_bus_name: Name of the first bus connected to the line.
        :param second_bus_name: Name of the second bus connected to the line.
        :param parallel_id: Parallel ID of this line on the branch between the two buses.
        :param fault_position: Distance (between 0 and 1) of the fault from the first bus.
        :param fault_resistance: Resistance associated to the fault in case of impedance fault.
        :param fault_reactance: Reactance associated to the fault in case of impedance fault.
        """
        if fault_position == 0 or fault_position == 1:
            # A fault at position 0 or 1 is a bus fault and not a line fault
            raise ValueError(first_bus_name, second_bus_name)
        self.time = time
        self.first_bus_name = first_bus_name
        self.second_bus_name = second_bus_name
        self.parallel_id = parallel_id
        self.fault_position = fault_position
        self.fault_resistance = fault_resistance
        self.fault_reactance = fault_reactance

    def __repr__(self):
        """
        repr  .
        
        :return: Return value.
        """
        return (
            f"Line short circuit: Branch=[{self.first_bus_name}, {self.second_bus_name}] "
            f"Parallel ID=[{self.parallel_id}] Position=[{self.fault_position}] "
            f"R=[{self.fault_resistance}] X=[{self.fault_reactance}]"
        )

    def apply_to_network(self, network: Network):
        """
        Apply the event to the network given as argument.
        This method modifies the network given as argument according to the event.
        
        :param network: The network to which the event must be applied.
        :return: A boolean indicator stating whether the fault is relevant to study.
        """
        if self.fault_resistance != 0 or self.fault_reactance != 0:
            raise NotImplementedError("Impedance faults are not supported.")

        # Get line
        first_bus_name = self.first_bus_name
        second_bus_name = self.second_bus_name
        branch = network.get_branch(first_bus_name, second_bus_name)
        line = branch[self.parallel_id]
        if type(line) != Line:
            raise TypeError(
                first_bus_name, second_bus_name, self.parallel_id, type(line), Line.__name__
            )

        if not line.closed:
            if line.open:
                # A short circuit on a line open on one side is possible
                print("Short circuit happening on a line open on one side only, carrying execution")
            else:
                # A short circuit on a disconnected line is irrelevant to study
                print("Event happening to a disconnected line:")
                print(self.__repr__())
                return False

        # Check if event bus order is same as branch bus order
        fault_position = self.fault_position
        if branch.first_bus.name != self.first_bus_name:
            first_bus_name = second_bus_name
            second_bus_name = self.first_bus_name
            fault_position = 1 - self.fault_position

        # Get line admittance
        line_admittance = line.admittance_pu

        # Add fictive load on first bus
        if line.closed_at_first_bus:
            load_admittance = line_admittance / fault_position
            if load_admittance != 0j:
                # Add load only if admittance is not 0
                branch.first_bus.add_load(
                    FictiveLoad(
                        name=f"FICT_LOAD_{self.parallel_id}_{second_bus_name}_{first_bus_name}",
                        bus=branch.first_bus,
                        admittance=load_admittance
                    )
                )

        # Add fictive load on second bus
        if line.closed_at_second_bus:
            load_admittance = line_admittance / (1 - fault_position)
            if load_admittance != 0j:
                # Add load only if admittance is not 0
                branch.second_bus.add_load(
                    FictiveLoad(
                        name=f"FICT_LOAD_{self.parallel_id}_{first_bus_name}_{second_bus_name}",
                        bus=branch.second_bus,
                        admittance=load_admittance
                    )
                )

        # Set short circuit on line
        line.metal_short_circuited = True

        return True


    def get_nearest_bus(self, network: Network) -> Bus:
        """
        Get the bus that is the nearest to the fault.
        
        :param network: Network in which the bus must be found.
        :return: The nearest bus to the fault.
        """
        # Get line
        branch = network.get_branch(self.first_bus_name, self.second_bus_name)
        return branch.first_bus if self.fault_position <= 0.5 else branch.second_bus

    pass


def create_line_short_circuit_event(event_data: dict) -> LineShortCircuitEvent:
    """
    Create a line short circuit event based on input event data.
    
    :param event_data: The event data.
    :return: A line short circuit event based on the event data.
    """
    return LineShortCircuitEvent(
        time=event_data['time'],
        first_bus_name=event_data['first_bus_name'],
        second_bus_name=event_data['second_bus_name'],
        parallel_id=event_data['parallel_id'],
        fault_position=event_data['fault_position'],
        fault_resistance=event_data['fault_resistance'],
        fault_reactance=event_data['fault_reactance']
    )


def parse_line_short_circuit_from_eurostag(event_data: dict) -> LineShortCircuitEvent:
    """
    Parse a line short circuit event from Eurostag data.
    
    :param event_data: Dictionary with the event data from eurostag file.
    :return: Parsed LineShortCircuitEvent.
    """
    return LineShortCircuitEvent(
        time=float(event_data["time"]),
        first_bus_name=event_data['sending_node'],
        second_bus_name=event_data['receiving_node'],
        parallel_id=event_data['parallel_index'],
        fault_position=float(event_data['short_circuit_distance']) / 100.0,
        fault_resistance=float(event_data['resistance']),
        fault_reactance=float(event_data['reactance'])
    )
