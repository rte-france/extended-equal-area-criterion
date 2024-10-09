# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List, Tuple

from deeac.domain.ports.events import EventParser
import deeac.domain.ports.dtos.events as dto_events
from deeac.domain.models.events import (
    FailureEvent, MitigationEvent, LineShortCircuitEvent, BusShortCircuitEvent, BranchEvent, BreakerEvent,
    BusShortCircuitClearingEvent, LineShortCircuitClearingEvent
)

# Mapping between event DTOs and models
EVENTS_MAPPING = {
    dto_events.LineShortCircuitEvent: LineShortCircuitEvent,
    dto_events.BusShortCircuitEvent: BusShortCircuitEvent,
    dto_events.BreakerEvent: BreakerEvent,
    dto_events.BranchEvent: BranchEvent,
    dto_events.BusShortCircuitClearingEvent: BusShortCircuitClearingEvent,
    dto_events.LineShortCircuitClearingEvent: LineShortCircuitClearingEvent
}


class EventLoader:
    """
    Service to load events in the models based on an event parser.
    """

    def __init__(self, event_parser: EventParser):
        """
        Initialize the event loader.

        :param event_parser: Event parser in charge of parsing the input events.
        """
        self.event_parser = event_parser

    def load_events(self) -> Tuple[List[FailureEvent], List[MitigationEvent]]:
        """
        Load failure and mitigation events.

        :return: A tuple containing repectively the lists of the loaded failure and mitigation events.
        """
        # Parse event data
        parsed_events = self.event_parser.parse_events()

        # Create the events based on the parsed data
        failure_events = []
        mitigtation_events = []
        for event_data in parsed_events:
            event = EVENTS_MAPPING[type(event_data)].create_event(event_data)
            if isinstance(event, MitigationEvent):
                mitigtation_events.append(event)
            else:
                failure_events.append(event)
        return (failure_events, mitigtation_events)
