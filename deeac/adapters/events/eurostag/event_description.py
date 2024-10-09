# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from enum import Enum
from typing import Dict, Tuple, Type
from pydantic import ValidationError

from .dtos import EventData
from .exceptions import EventDataValidationException
from deeac.domain.exceptions import DEEACExceptionList


class EventType(Enum):
    """
    Type of event record that can be found in an Eurostag SEQ file.
    """
    BREAKER_OPEN = 'BRANC OP'
    BREAKER_CLOSE = 'BRANC CL'
    NODE_FAULT = 'FAULTATN'
    NODE_CLEAR = 'CLEARB'
    LINE_FAULT = 'FAULTONL'
    LINE_CLEAR = 'CLEARL'
    IMPEDANCE_MOD = 'MODCAP'
    GENERATOR_START = 'GENER OP'
    GENERATOR_STOP = 'GENER CL'
    STATOR_OPEN = 'STAT  OP'
    STATOR_CLOSE = 'STAT  CL'
    SETPOINT = 'SETPOINT'
    AUTOMATON_SETPOINT = 'SETPMACR'
    MACHINE_SETPOINT_AREA = 'SET AREA'
    MACHINE_SETPOINT = 'SET MACH'
    TFO_TAP = 'TAP   MO'
    LOAD_MODIFICATION = 'LOAD  SW'
    LOAD_VARIATION_AREA = 'LOAD VAR'
    LOAD_VARIATION_NODE = 'LOAD VNO'
    LOAD_TIME = 'LOAD  MT'
    A14_AUTOMATON = 'AUTOM MO'
    DEVICE_ACTIVATION = 'AUTOM AC'
    BANK_MODIFICATION = 'CAP BANK'
    SCENARIO = 'PARA MOD'
    SYSTEM_STATE_SAVE = 'SAVE'
    EIGEN_VALUES = 'EIGNEVAL'
    LINEA_EXPORT = 'LINEAR'
    SIMULATION_STOP = 'STOP'
    SIMULATION_PAUSE = 'PAUSE'


class EventDescription:
    """
    Description of a record that modeling an event that can be found in an Eurostag SEQ file.
    A record format defines the fields of interest, and for each field, an interval [start, end[ specifying the column
    numbers where it is stored in the line.
    """

    def __init__(self, format: Dict[str, Tuple[int, int]], event_data: Type[EventData]):
        """
        Initilization.

        :param format: Expected format for a record having this description.
        :param event_data: Type of event data represented by this description.
        """
        self.format = format
        self.event_data = event_data

    def parse_event(self, record: str) -> EventData:
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
            return self.event_data(**parsed_record)
        except ValidationError as e:
            exception_list = DEEACExceptionList([])
            # Get validation errors and create corresponding DEEAC exceptions
            for val_error in e.errors():
                exception_list.append(
                    EventDataValidationException(record, val_error["loc"], val_error["type"])
                )
            raise(exception_list)
