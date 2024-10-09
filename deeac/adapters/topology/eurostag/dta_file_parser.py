# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Union, Tuple

from .record_description import RecordType, RecordDescription
from .network_data_description import NetworkDataDescription
from .file_parser import EurostagFileParser, FileType
from .dtos import GeneratorDynamicPart


class DtaRecordType(RecordType):
    """
    Types of record in the .dta file
    """
    HEADER = 'HEADER'
    DYNAMIC_ZONE = 'ZD'
    FULL_INTERNAL_PARAM_GENERATOR = 'M1'
    FULL_EXTERNAL_PARAM_GENERATOR = 'M2'
    SIMPL_INTERNAL_PARAM_GENERATOR = 'M5'
    SIMPL_EXTERNAL_PARAM_GENERATOR = 'M6'
    FULL_INDUCTION_MOTOR = 'M10'
    SIMPL_INDUCTION_MOTOR = 'M11'
    FULL_INDUCTION_MOTOR_WITH_TORQUE = 'M13'
    SIMPL_INDUCTION_MOTOR_WITH_TORQUE = 'M14'
    DOUBLE_FED_INDUCTION_MACHINE = 'M15'
    PLOAD_QLOAD_INJECTOR = 'M20'
    BG_INJECTOR = 'M21'
    I_PHI_INJECTOR = 'M22'
    IR_II_INJECTOR = 'M23'
    CONVERTER = 'M50'
    MACROBLOCK = 'R'
    GENERIC_MOTOR = 'GM'
    LOAD_PATTERN = 'LOADP'
    LOAD_BEHAVIOR = 'CH'
    INFINITE_NODE = 'II'
    CONTROLLED_TRANSFORMER = 'TRF'
    TRANSFORMER_MACROBLOCK = 'RTFO'
    CONTROLLED_BANK = 'BAT'
    SENSITIVITY_ADMITTANCE_FREQ = 'FREQ'
    MACHINE_ANGLES = 'ANGLEABS'
    AUTOMATIC_DEVICE_1 = 'A01'
    AUTOMATIC_DEVICE_2 = 'A02'
    AUTOMATIC_DEVICE_10 = 'A10'
    AUTOMATIC_DEVICE_11 = 'A11'
    AUTOMATIC_DEVICE_12 = 'A12'
    AUTOMATIC_DEVICE_13 = 'A13'
    AUTOMATIC_DEVICE_14 = 'A14'
    AUTOMATIC_DEVICE_15 = 'A15'
    AUTOMATIC_DEVICE_16 = 'A16'
    AUTOMATIC_DEVICE_17 = 'A17'
    AUTOMATIC_DEVICE_18 = 'A18'
    AUTOMATIC_DEVICE_19 = 'A19'
    AUTOMATIC_DEVICE_20 = 'A20'
    AUTOMATIC_DEVICE_21 = 'A21'
    MACRO_AUTOMATON = 'MA'
    MACRO_AUTOMATON_MACROBLOCK = 'RMA'
    USER_AUTOMATON = 'A33'
    USER_AUTOMATON_EVENT = 'EV'


"""
Description of the network data of interest in the Eurostag .dta file.
Network data corresponds to one or several specific records of a .dta file, and represents the data associated to a
network element (e.g. the dynamic data of a generator).
A record corresponds to a line of the file.

A NetworkDataDescription is the description of the records representing the data of a network element.
The order of the record descriptions corresponds to the record numbers.
The description specifies the maximum number of records that can be found in the corresponding network data, as well as
the kind of NetworkData it describes.

A record length defines the number of characters in the corresponding line.
A record format defines the fields of interest, and for each field, an interval [start, end[ specifying the column
numbers where it is stored in the line.

"""
DTA_FILE_DESCRIPTION = {
    DtaRecordType.FULL_EXTERNAL_PARAM_GENERATOR: NetworkDataDescription(
        max_nb_records=6,
        record_descriptions=[
            # First record is ignored
            RecordDescription(
                min_length=30,
                max_length=39,
                format={},
            ),
            RecordDescription(
                min_length=71,
                max_length=71,
                format={
                    'name': (0, 8),
                    'rated_apparent_power': (18, 26),
                    'base_voltage_machine_side': (27, 35),
                    'inertia_constant': (63, 71)
                }
            ),
            RecordDescription(
                min_length=71,
                max_length=80,
                format={
                    'direct_transient_reactance': (36, 44)
                }
            ),
            # Next records are ignored
            RecordDescription(
                min_length=75,
                max_length=82,
                format={}
            ),
            RecordDescription(
                min_length=71,
                max_length=71,
                format={}
            ),
            RecordDescription(
                min_length=44,
                max_length=80,
                format={}
            )
        ],
        network_data=GeneratorDynamicPart
    )
}


class DtaEurostagFileParser(EurostagFileParser):
    """
    Eurostag .dta file parser.
    LIMITATIONS:
        1. The number of record descriptions must match the number of records for the corresponding network data
           in the input file.
        2. Only record types with maximum 3 characters are supported.
    """

    def __init__(self, file_path: str):
        """
        Initialize the object specifying the type and description of the corresponding file.

        :param file_path: Path to the .dta file to read.
        """
        # Previous record read from the file (type + number)
        self._prev_record_type: RecordType = None
        self._prev_record_nb: int = 0
        # Lengths of all the record types that may appear in the file
        self._record_type_lengths = sorted({len(e.value) for e in DtaRecordType}, reverse=True)

        # Generate record types only once to increase performances
        self._record_types = {}
        for type in DtaRecordType:
            self._record_types[type.value] = type

        super().__init__(
            file_type=FileType.DTA,
            file_description=DTA_FILE_DESCRIPTION,
            file_path=file_path
        )

    def _identify_record(self, file_line: str) -> Union[Tuple[RecordType, int], None]:
        """
        Identify a record represented by a line from a .dta Eurostag file.

        :param file_line: A line of a .dta Eurostag file
        :return: A tuple containing the type of record and its number, if the record is of interest, otherwise None.
        """
        # Check if empty record
        if file_line == "":
            self._prev_record_nb = 0
            self._prev_record_type = None
            return None

        if self._prev_record_type is not None:
            # Record of interest previously observed
            nb_record_descriptions = len(self.file_description[self._prev_record_type].record_descriptions)
            if self._prev_record_nb < nb_record_descriptions:
                # Minimum number of records not reached for current element
                record_nb = self._prev_record_nb + 1
                self._prev_record_nb = record_nb
                return (self._prev_record_type, record_nb)

        # Search for new record type (longest prefix match)
        record_type = None
        for i in self._record_type_lengths:
            line_rtype = file_line[0:i]
            if line_rtype in self._record_types:
                # New type or record
                record_type = self._record_types[line_rtype]
                break

        if record_type is None or record_type not in self.file_description:
            # Not a record of interest
            return None

        # Update previous record
        self._prev_record_nb = 1
        self._prev_record_type = record_type

        return (record_type, 1)
