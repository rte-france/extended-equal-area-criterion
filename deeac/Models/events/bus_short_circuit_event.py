"""
Module for bus_short_circuit_event.

:module: bus_short_circuit_event
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import sys

from deeac.Models.bus import Bus
from deeac.Models.load import FictiveLoad
from deeac.Models.network import Network

from deeac.Models.events.failure_event import FailureEvent


class BusShortCircuitEvent(FailureEvent):
    """
    Busshortcircuitevent.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar time: time.
    :ivar bus_name: bus name.
    :ivar fault_resistance: fault resistance.
    :ivar fault_reactance: fault reactance.
    """

    def __init__(
        self, time: float, bus_name: str, fault_resistance: float = 0, fault_reactance: float = 0
    ):
        """
        Initialize the event.
        
        :param bus_name: Name of the bus where the short circuit happens.
        :param fault_resistance: Resistance associated to the fault in case of impedance fault.
        :param fault_reactance: Reactance associated to the fault in case of impedance fault.
        """
        self.time = time
        self.bus_name = bus_name
        # Use epsilon for impedance to avoid infinite values in computations
        if fault_resistance == 0:
            fault_resistance = sys.float_info.epsilon
        self.fault_resistance = fault_resistance
        self.fault_reactance = fault_reactance

    def __repr__(self):
        """
        repr  .
        
        :return: Return value.
        """
        return (
            f"Bus short circuit: Bus=[{self.bus_name}] R=[{self.fault_resistance}] X=[{self.fault_reactance}]"
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
        admittance = 1 / complex(self.fault_resistance, self.fault_reactance)

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


    pass


def create_bus_short_circuit_event(event_data: dict) -> BusShortCircuitEvent:
    """
    Create a bus short circuit event based on input event data.
    
    :param event_data: The event data.
    :return: A bus short circuit event based on the event data.
    """
    return BusShortCircuitEvent(
        time=event_data['time'],
        bus_name=event_data['bus_name'],
        fault_resistance=event_data['fault_resistance'],
        fault_reactance=event_data['fault_reactance'],
    )


def parse_bus_short_circuit_from_eurostag(event_data: dict) -> BusShortCircuitEvent:
    """
    Parse a bus short circuit event from Eurostag data.
    
    :param event_data: Dictionary with the event data from eurostag file.
    :return: Parsed BusShortCircuitEvent.
    """
    return BusShortCircuitEvent(
        time=float(event_data['time']),
        bus_name=event_data['node'],
        fault_resistance=float(event_data['resistance']),
        fault_reactance=float(event_data['reactance'])
    )
