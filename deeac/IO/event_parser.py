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

from typing import List
from abc import ABC, abstractmethod

from deeac.Models.events.event import Event


class EventParser(ABC):
    """
    Eventparser.
    
    Rationale:
        This class handles input parsing or configuration shaping. It converts
        external data into the explicit objects consumed by the EEAC pipeline.
    
    :summary: Class metadata.
    """
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def parse_events(self) -> List[Event]:
        """
        Parse events from input.
        
        :return: The list of events extracted from the input.
        """
        pass
