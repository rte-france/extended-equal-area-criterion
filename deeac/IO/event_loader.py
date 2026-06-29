"""
Module for event_loader.

:module: event_loader
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List, Tuple

from deeac.IO.event_parser import EventParser

from deeac.Models.events.mitigation_event import MitigationEvent
from deeac.Models.events.failure_event import FailureEvent


class EventLoader:
    """
    Eventloader.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar event_parser: event parser.
    """

    def __init__(self, event_parser: EventParser):
        """
        Initialize the event loader.
        
        :param event_parser: Event parser in charge of parsing the input events.
        """
        self.event_parser: EventParser = event_parser

    def load_events(self) -> Tuple[List[FailureEvent], List[MitigationEvent]]:
        """
        Load failure and mitigation events.
        
        :return: A tuple containing respectively the lists of the
        loaded failure and mitigation events.
        """
        # Parse event data
        parsed_events = self.event_parser.parse_events()

        # Create the events based on the parsed data
        failure_events = []
        mitigation_events = []
        for event in parsed_events:

            if isinstance(event, MitigationEvent):
                mitigation_events.append(event)
            else:
                failure_events.append(event)

        return failure_events, mitigation_events
