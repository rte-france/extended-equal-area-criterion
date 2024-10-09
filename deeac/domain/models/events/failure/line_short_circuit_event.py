# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.domain.models import Network, Line, Value, Unit, FictiveLoad, Bus
from deeac.domain.exceptions import UnexpectedBranchElementException, LineShortCircuitException
from deeac.domain.ports.dtos.events import LineShortCircuitEvent as LineShortCircuitEventDto
from .failure_event import FailureEvent


class LineShortCircuitEvent(FailureEvent):
    """
    Class that models a line short circuit.
    """

    def __init__(
        self, first_bus_name: str, second_bus_name: str, parallel_id: str, fault_position: float,
        fault_resistance: Value = Value(0, Unit.OHM), fault_reactance: Value = Value(0, Unit.OHM)
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
            raise LineShortCircuitException(first_bus_name, second_bus_name)
        self.first_bus_name = first_bus_name
        self.second_bus_name = second_bus_name
        self.parallel_id = parallel_id
        self.fault_position = fault_position
        self.fault_resistance = fault_resistance
        self.fault_reactance = fault_reactance

    def __repr__(self):
        """
        Representation of a line short circuit.
        """
        return (
            f"Line short circuit: Branch=[{self.first_bus_name}, {self.second_bus_name}] "
            f"Parallel ID=[{self.parallel_id}] Position=[{self.fault_position}] "
            f"R=[{self.fault_resistance}] X=[{self.fault_reactance}]"
        )

    @classmethod
    def create_event(cls, event_data: LineShortCircuitEventDto) -> 'LineShortCircuitEvent':
        """
        Create a line short circuit event based on input event data.

        :param event_data: The event data.
        :return: A line short circuit event based on the event data.
        """
        return cls(
            first_bus_name=event_data.first_bus_name,
            second_bus_name=event_data.second_bus_name,
            parallel_id=event_data.parallel_id,
            fault_position=event_data.fault_position,
            fault_resistance=Value(
                Value.from_dto(event_data.fault_resistance).to_unit(Unit.OHM),
                Unit.OHM
            ),
            fault_reactance=Value(
                Value.from_dto(event_data.fault_reactance).to_unit(Unit.OHM),
                Unit.OHM
            )
        )

    def apply_to_network(self, network: Network):
        """
        Apply the event to the network given as argument.
        This method modifies the network given as argument according to the event.

        :param network: The network to which the event must be applied.
        :raise ElementNotFoundException if no branch can be found between the two buses in the network.
        :raise ParallelException if no element is at the specified parallel ID on the branch.
        :raise UnexpectedBranchElementException if element at the specified parallel ID is not a line.
        :return: A boolean indicator stating whether the fault is relevant to study.
        """
        if self.fault_resistance.to_unit(Unit.OHM) != 0 or self.fault_reactance.to_unit(Unit.OHM) != 0:
            raise NotImplementedError("Impedance faults are not supported.")

        # Get line
        first_bus_name = self.first_bus_name
        second_bus_name = self.second_bus_name
        branch = network.get_branch(first_bus_name, second_bus_name)
        line = branch[self.parallel_id]
        if type(line) != Line:
            raise UnexpectedBranchElementException(
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
        line_admittance = line.admittance

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
