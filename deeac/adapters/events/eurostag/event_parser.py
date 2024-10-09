# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List

from deeac.domain.exceptions import DEEACExceptionCollector
from deeac.domain.ports.dtos.events import (
    Event, BranchEvent, BreakerEvent, LineShortCircuitEvent, BusShortCircuitEvent, BreakerPosition,
    LineShortCircuitClearingEvent, BusShortCircuitClearingEvent
)
from deeac.domain.ports.dtos import Value, Unit
from deeac.domain.ports.events import EventParser
from .event_description import EventType, EventDescription
from deeac.adapters.events.eurostag import dtos as eurostag_dtos

# Name of the section in the file dedicated to the events
EVENT_SECTION_NAME = "EVENTS"
# Start and end columns of the type in an event record
EVENT_TYPE_START = 9
EVENT_TYPE_END = 17

# Description of the records of interest in the file
EVENT_DESCRIPTION = {
    EventType.BREAKER_OPEN: EventDescription(
        format={
            'time': (0, 8),
            'sending_node': (18, 26),
            'receiving_node': (27, 35),
            'parallel_index': (36, 37),
            'position': (38, 39),
            'branch_type': (51, 52),
            'first_coupled_node': (53, 61),
            'second_coupled_node': (62, 70),
            'coupling_index': (71, 72)
        },
        event_data=eurostag_dtos.BreakerOpeningEvent
    ),
    EventType.BREAKER_CLOSE: EventDescription(
        format={
            'time': (0, 8),
            'sending_node': (18, 26),
            'receiving_node': (27, 35),
            'parallel_index': (36, 37),
            'opening_side': (38, 39),
            'branch_type': (51, 52),
            'first_coupled_node': (53, 61),
            'second_coupled_node': (62, 70)
        },
        event_data=eurostag_dtos.BreakerClosingEvent
    ),
    EventType.NODE_FAULT: EventDescription(
        format={
            'time': (0, 8),
            'node': (18, 26),
            'resistance': (56, 64),
            'reactance': (65, 73)
        },
        event_data=eurostag_dtos.NodeShortCircuitEvent
    ),
    EventType.NODE_CLEAR: EventDescription(
        format={
            'time': (0, 8),
            'node': (18, 26)
        },
        event_data=eurostag_dtos.NodeShortCircuitClearingEvent
    ),
    EventType.LINE_FAULT: EventDescription(
        format={
            'time': (0, 8),
            'sending_node': (18, 26),
            'receiving_node': (27, 35),
            'parallel_index': (36, 37),
            'short_circuit_distance': (47, 55),
            'resistance': (56, 64),
            'reactance': (65, 73)
        },
        event_data=eurostag_dtos.LineShortCircuitEvent
    ),
    EventType.LINE_CLEAR: EventDescription(
        format={
            'time': (0, 8),
            'sending_node': (18, 26),
            'receiving_node': (27, 35),
            'parallel_index': (36, 37)
        },
        event_data=eurostag_dtos.LineShortCircuitClearingEvent
    ),
}


class EurostagEventParser(EventParser):
    """
    Parse a Eurostag event file.
    These events are extracted from a .seq file.
    """

    def __init__(self, eurostag_event_file: str, protection_delay: float = 0):
        """
        Initialize the parser.

        :param eurostag_event_file: File containing the event data.
        """
        self.eurostag_event_file = eurostag_event_file

        self._is_event_section = False
        self._events = list()
        self._protection_delay = protection_delay

        # Exception collector
        self._exception_collector: DEEACExceptionCollector = DEEACExceptionCollector()

        # Generate event types only once to increase performances
        self._event_types = {}
        for type in EventType:
            self._event_types[type.value] = type

    @property
    def short_circuit_delay(self):
        """
        If the first and last BusShortCircuitEvent are separated from more than 15ms consider it "degraded mode"
        """
        if not self._events:
            raise ValueError("No event instantiated yet")

        for event in self._events:
            if isinstance(event, BranchEvent) or isinstance(event, BreakerEvent):
                first_time = event.time
                break
        else:
            return False

        for event in self._events[::-1]:
            if isinstance(event, BranchEvent) or isinstance(event, BreakerEvent):
                last_time = event.time
                break
        else:
            raise ValueError("No BusShortCircuitEvent event found")

        # 10.109 - 10.094 = 0.015000000000000568 which is superior 0.15
        time_difference = int((last_time - first_time) * 1e3)
        if time_difference > self._protection_delay:
            return time_difference

    def parse_events(self) -> List[Event]:
        """
        Parse the sequence file.

        :return: A list of the events extracted from the file.
        """
        self._exception_collector.reset()

        # Reset loading variables
        self._is_event_section = False
        self._events = list()

        try:
            with open(self.eurostag_event_file, encoding='utf-8') as file:
                for line in file:
                    with self._exception_collector:
                        self._get_event_from_line(line)

        # If there is an encoding error, restart the parsing
        except UnicodeDecodeError:
            with open(self.eurostag_event_file, encoding='latin-1') as file:
                for line in file:
                    with self._exception_collector:
                        self._get_event_from_line(line)

        # Raise exceptions if any
        self._exception_collector.raise_for_exception()

        # Return events
        return self._events

    def _get_event_from_line(self, line: str):
        """
        Extracts the events from one line of the event file
        :param line: one line of the event file to parse
        """
        stripped_line = line.strip()
        if stripped_line == EVENT_SECTION_NAME:
            self._is_event_section = True
            # Entering events section
            return

        if stripped_line == "" or not self._is_event_section:
            # Skip empty lines and sections other than events
            return

        # Get event type and data
        event_type = self._event_types[line[EVENT_TYPE_START:EVENT_TYPE_END].strip()]
        try:
            event_description = EVENT_DESCRIPTION[event_type]
        except KeyError:
            # Event not supported
            return
        event_data = event_description.parse_event(line)

        event_dict = {"time": event_data.time}
        if isinstance(event_data, eurostag_dtos.BreakerEvent):
            # Check if opening or closing event
            if type(event_data) == eurostag_dtos.BreakerOpeningEvent:
                event_dict["breaker_closed"] = False
            else:
                event_dict["breaker_closed"] = True
            if event_data.branch_type is None:
                # Event related to a line or transformer
                event_dict["first_bus_name"] = event_data.sending_node
                event_dict["second_bus_name"] = event_data.receiving_node
                event_dict["parallel_id"] = event_data.parallel_index
                if event_data.position == eurostag_dtos.BreakerPosition.SENDING_NODE:
                    event_dict["breaker_position"] = BreakerPosition.FIRST_BUS
                else:
                    event_dict["breaker_position"] = BreakerPosition.SECOND_BUS
                self._events.append(BranchEvent(**event_dict))
            elif event_data.branch_type == eurostag_dtos.BranchType.COUPLING_DEVICE:
                # Event related to a coupling device
                event_dict["first_bus_name"] = event_data.first_coupled_node
                event_dict["second_bus_name"] = event_data.second_coupled_node
                event_dict["parallel_id"] = event_data.coupling_index
                self._events.append(BreakerEvent(**event_dict))
            else:
                raise NotImplementedError(
                    f"[Event parser] Opening/closing an element of type {event_data.branch_type} "
                    f"is not supported."
                )
        elif type(event_data) == eurostag_dtos.LineShortCircuitEvent:
            # Event related to a line short circuit
            event_dict["first_bus_name"] = event_data.sending_node
            event_dict["second_bus_name"] = event_data.receiving_node
            event_dict["parallel_id"] = event_data.parallel_index
            event_dict["fault_position"] = event_data.short_circuit_distance / 100.0
            event_dict["fault_resistance"] = Value(value=event_data.resistance, unit=Unit.OHM)
            event_dict["fault_reactance"] = Value(value=event_data.reactance, unit=Unit.OHM)
            self._events.append(LineShortCircuitEvent(**event_dict))
        elif type(event_data) == eurostag_dtos.LineShortCircuitClearingEvent:
            # Event related to a line short circuit clearing
            event_dict["first_bus_name"] = event_data.sending_node
            event_dict["second_bus_name"] = event_data.receiving_node
            event_dict["parallel_id"] = event_data.parallel_index
            self._events.append(LineShortCircuitClearingEvent(**event_dict))
        elif type(event_data) == eurostag_dtos.NodeShortCircuitEvent:
            # Event related to a bus short circuit
            event_dict["bus_name"] = event_data.node
            event_dict["fault_resistance"] = Value(value=event_data.resistance, unit=Unit.OHM)
            event_dict["fault_reactance"] = Value(value=event_data.reactance, unit=Unit.OHM)
            self._events.append(BusShortCircuitEvent(**event_dict))
        elif type(event_data) == eurostag_dtos.NodeShortCircuitClearingEvent:
            # Event related to a bus short circuit clearing
            event_dict["bus_name"] = event_data.node
            self._events.append(BusShortCircuitClearingEvent(**event_dict))
        else:
            raise NotImplementedError(f"[Event parser] Events of type {event_type} are not supported.")
