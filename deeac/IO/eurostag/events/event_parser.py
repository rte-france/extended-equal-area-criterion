"""
Module for event_parser.

:module: event_parser
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import os
from typing import List

from deeac.Models.events.branch_event import BranchEvent

from deeac.Models.events.event import Event
from deeac.Models.events.breaker_event import (
    parse_breaker_opening_from_eurostag,
    parse_breaker_closing_from_eurostag, BreakerEvent,
)
from deeac.Models.events.line_short_circuit_event import parse_line_short_circuit_from_eurostag
from deeac.Models.events.line_short_circuit_clearing_event import parse_line_short_circuit_clearing_from_eurostag
from deeac.Models.events.bus_short_circuit_event import parse_bus_short_circuit_from_eurostag
from deeac.Models.events.bus_short_circuit_clearing_event import parse_bus_short_circuit_clearing_from_eurostag

from deeac.enums import EventType
from deeac.IO.event_parser import EventParser
from deeac.IO.eurostag.events.event_description import EventDescription

# Name of the section in the file dedicated to the events
EVENT_SECTION_NAME = "EVENTS"
# Start and end columns of the type in an event record
EVENT_TYPE_START = 9
EVENT_TYPE_END = 17

# Description of the records of interest in the file
EVENT_DESCRIPTION = {
    EventType.BREAKER_OPEN: EventDescription(
        frmt={
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
        event_parser=parse_breaker_opening_from_eurostag
    ),
    EventType.BREAKER_CLOSE: EventDescription(
        frmt={
            'time': (0, 8),
            'sending_node': (18, 26),
            'receiving_node': (27, 35),
            'parallel_index': (36, 37),
            'opening_side': (38, 39),
            'branch_type': (51, 52),
            'first_coupled_node': (53, 61),
            'second_coupled_node': (62, 70)
        },
        event_parser=parse_breaker_closing_from_eurostag
    ),
    EventType.NODE_FAULT: EventDescription(
        frmt={
            'time': (0, 8),
            'node': (18, 26),
            'resistance': (56, 64),
            'reactance': (65, 73)
        },
        event_parser=parse_bus_short_circuit_from_eurostag
    ),
    EventType.NODE_CLEAR: EventDescription(
        frmt={
            'time': (0, 8),
            'node': (18, 26)
        },
        event_parser=parse_bus_short_circuit_clearing_from_eurostag
    ),
    EventType.LINE_FAULT: EventDescription(
        frmt={
            'time': (0, 8),
            'sending_node': (18, 26),
            'receiving_node': (27, 35),
            'parallel_index': (36, 37),
            'short_circuit_distance': (47, 55),
            'resistance': (56, 64),
            'reactance': (65, 73)
        },
        event_parser=parse_line_short_circuit_from_eurostag
    ),
    EventType.LINE_CLEAR: EventDescription(
        frmt={
            'time': (0, 8),
            'sending_node': (18, 26),
            'receiving_node': (27, 35),
            'parallel_index': (36, 37)
        },
        event_parser=parse_line_short_circuit_clearing_from_eurostag
    ),
}


class EurostagEventParser(EventParser):
    """
    Eurostageventparser.
    
    Rationale:
        This class handles input parsing or configuration shaping. It converts
        external data into the explicit objects consumed by the EEAC pipeline.
    
    :ivar eurostag_event_file: eurostag event file.
    :ivar protection_delay: protection delay.
    """

    def __init__(self, eurostag_event_file: str, protection_delay: float = 0):
        """
        Initialize the parser.
        
        :param eurostag_event_file: File containing the event data.
        """
        super().__init__(name=os.path.splitext(os.path.split(eurostag_event_file)[1])[0])

        self.eurostag_event_file = eurostag_event_file

        self._is_event_section = False
        self._events = list()
        self._protection_delay = protection_delay

        # Exception collector placeholder (list of exceptions if needed)
        self._exception_collector: List[Exception] = []

        # Generate event types only once to increase performances
        self._event_types = {}
        for tpe in EventType:
            self._event_types[tpe.value] = tpe

    @property
    def short_circuit_delay(self):
        """
        Short circuit delay.
        
        :return: Return value.
        """
        if not self._events:
            return False

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
            return False

        # 10.109 - 10.094 = 0.015000000000000568 which is superior 0.15
        time_difference = int((last_time - first_time) * 1e3)
        if time_difference > self._protection_delay:
            return time_difference

        return None

    def parse_events(self) -> List[Event]:
        """
        Parse the sequence file.
        
        :return: A list of the events extracted from the file.
        """
        self._exception_collector = []

        # Reset loading variables
        self._is_event_section = False
        self._events = list()

        def _parse_with_encoding(encoding: str) -> None:
            with open(self.eurostag_event_file, encoding=encoding) as file:
                for line in file:
                    try:
                        self._get_event_from_line(line)
                    except Exception as exc:
                        self._exception_collector.append(exc)

        try:
            _parse_with_encoding('utf-8')
        except UnicodeDecodeError:
            # If there is an encoding error, restart the parsing
            _parse_with_encoding('latin-1')

        if self._exception_collector:
            raise ValueError(f"Event parsing failed with {len(self._exception_collector)} error(s).")

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
        event = event_description.parse_event(line)
        self._events.append(event)
