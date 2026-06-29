"""
Module for event_description.

:module: event_description
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Callable, Dict, Tuple
from deeac.Models.events.event import Event


class EventDescription:
    """
    Eventdescription.
    
    Rationale:
        This class handles input parsing or configuration shaping. It converts
        external data into the explicit objects consumed by the EEAC pipeline.
    
    :ivar frmt: frmt.
    :ivar event_parser: event parser.
    """

    def __init__(self, frmt: Dict[str, Tuple[int, int]], event_parser: Callable[[dict], Event]):
        """
        Initialization.
        
        :param frmt: Expected format for a record having this description.
        :param event_parser: Parser function for the event data represented by this description.
        """
        self.format = frmt
        self.event_parser = event_parser

    def parse_event(self, record: str) -> Event:  # TODO: Think about typing when done with the event creation
        """
        Parse an event record according to its description.
        
        :param record: The record to parse.
        :return: The corresponding event data.
        :raise DEEACExceptionList if the event data could not be retrieved.
        """
        parsed_record = dict()
        for name, (start, end) in self.format.items():
            record_field = record[start:end].strip()
            if record_field == "":
                # Replace empty strings by None
                record_field = None
            parsed_record[name] = record_field

        try:
            return self.event_parser(parsed_record)
        except:
            raise NotImplementedError("[Event parser] Events of this type are not supported.")

            # return self.event_data(**parsed_record)  # TODO: Never do this
        # except ValidationError as e:
        #     exception_list = DEEACExceptionList([])
        #     # Get validation errors and create corresponding DEEAC exceptions
        #     for val_error in e.errors():
        #         exception_list.append(
        #             EventDataValidationException(record, val_error["loc"], val_error["type"])
        #         )
        #     raise(exception_list)
