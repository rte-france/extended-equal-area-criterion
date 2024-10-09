# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Union, Tuple

from .file_parser import EurostagFileParser, FileType
from .network_data_description import NetworkDataDescription
from .record_description import RecordDescription, RecordType
from .dtos import (
    Node, SlackBus, CouplingDevice, Line, GeneratorStaticPart, Type1Transformer, Type8Transformer, Load,
    StaticVarCompensator, HVDCCurrentSourceConverter, HVDCVoltageSourceConverter, NetworkParameters, CapacitorBank
)


class EchRecordType(RecordType):
    """
    Types of record in the .ech file
    """
    HEADER = 'HEADER'
    START_OF_FILE = 'B'
    GENERAL_PARAMETERS = '9'
    SPECIAL_PARAMETER = 'SP'
    SPECIFIC_COMMENT = '8'
    GENERAL_COMMENT = 'GC'
    AC_ZONE = 'AA'
    NODE = '1'
    SLACK_BUS = '5'
    LINE = '3'
    COUPLING_DEVICE = '6'
    GENERATOR = 'G'
    TYPE1_TRANSFORMER = '41'
    TYPE2_TRANSFORMER = '42'
    TYPE4_TRANSFORMER = '44'
    TYPE8_TRANSFORMER = '48'
    TYPE9_TRANSFORMER = '49'
    DISSYMMETRICAL_BRANCHE = 'P'
    SERIAL_BRANCHE = 'SE'
    LOAD = 'CH'
    DC_ZONE = 'DA'
    DC_NODE = 'DC N'
    DC_LINK = 'DC L'
    SVC = 'SV'
    CAPACITOR_BANK = 'C'
    HVDC_CSC_CONVERTER = 'DC C'
    HVDC_VSC_CONVERTER = 'DC V'


"""
Description of the network data of interest in the Eurostag .ech file.
Network data correspond to one or several records of a .ech file, and mostly represent the data associated to a specific
record type (e.g. a transformer).
A record corresponds to a line of the file.
A record length defines the number of characters in the corresponding line.
A record format defines the fields of interest, and for each field, an interval [start, end[ specifying the column
numbers where it is stored in the line.
"""
ECH_FILE_DESCRIPTION = {
    EchRecordType.GENERAL_PARAMETERS: NetworkDataDescription(
        max_nb_records=1,
        network_data=NetworkParameters,
        record_descriptions=[
            RecordDescription(
                min_length=74,
                max_length=78,
                format={
                    'base_power': (66, 74)
                }
            )
        ]
    ),
    EchRecordType.NODE: NetworkDataDescription(
        max_nb_records=1,
        network_data=Node,
        record_descriptions=[
            RecordDescription(
                min_length=133,
                max_length=142,
                format={
                    'name': (3, 11),
                    'base_voltage': (84, 92)
                }
            )
        ]
    ),
    EchRecordType.SLACK_BUS: NetworkDataDescription(
        max_nb_records=1,
        network_data=SlackBus,
        record_descriptions=[
            RecordDescription(
                min_length=47,
                max_length=47,
                format={
                    'name': (3, 11),
                    'phase_angle': (39, 47)
                }
            )
        ]
    ),
    EchRecordType.COUPLING_DEVICE: NetworkDataDescription(
        max_nb_records=1,
        network_data=CouplingDevice,
        record_descriptions=[
            RecordDescription(
                min_length=38,
                max_length=47,
                format={
                    'sending_node': (2, 10),
                    'opening_code': (10, 11),
                    'receiving_node': (11, 19),
                    'parallel_index': (19, 20)
                }
            )
        ]
    ),
    EchRecordType.LINE: NetworkDataDescription(
        max_nb_records=1,
        network_data=Line,
        record_descriptions=[
            RecordDescription(
                min_length=83,
                max_length=92,
                format={
                    'sending_node': (2, 10),
                    'opening_code': (10, 11),
                    'receiving_node': (11, 19),
                    'parallel_index': (19, 20),
                    'resistance': (21, 29),
                    'reactance': (30, 38),
                    'semi_shunt_conductance': (39, 47),
                    'semi_shunt_susceptance': (48, 56),
                    'rated_apparent_power': (57, 65)
                }
            )
        ]
    ),
    EchRecordType.GENERATOR: NetworkDataDescription(
        max_nb_records=1,
        network_data=GeneratorStaticPart,
        record_descriptions=[
            RecordDescription(
                min_length=123,
                max_length=132,
                format={
                    'name': (3, 11),
                    'state': (12, 13),
                    'bus_name': (14, 22),
                    'min_active_power': (23, 31),
                    'active_power': (32, 40),
                    'max_active_power': (41, 49),
                    'min_reactive_power': (50, 58),
                    'reactive_power': (59, 67),
                    'max_reactive_power': (68, 76),
                    'regulating_mode': (77, 78),
                    'target_voltage': (79, 87),
                    'source': (124, 133)
                }
            )
        ]
    ),
    EchRecordType.TYPE1_TRANSFORMER: NetworkDataDescription(
        max_nb_records=1,
        network_data=Type1Transformer,
        record_descriptions=[
            RecordDescription(
                min_length=92,
                max_length=101,
                format={
                    'sending_node': (2, 10),
                    'opening_code': (10, 11),
                    'receiving_node': (11, 19),
                    'parallel_index': (19, 20),
                    'resistance': (21, 29),
                    'reactance': (30, 38),
                    'rated_apparent_power': (57, 65),
                    'transformation_ratio': (66, 74)
                }
            )
        ]
    ),
    EchRecordType.TYPE8_TRANSFORMER: NetworkDataDescription(
        max_nb_records=-1,
        network_data=Type8Transformer,
        record_descriptions=[
            RecordDescription(
                min_length=64,
                max_length=91,
                format={
                    'sending_node': (2, 10),
                    'opening_code': (10, 11),
                    'receiving_node': (11, 19),
                    'parallel_index': (19, 20),
                    'rated_apparent_power': (21, 29)
                }
            ),
            RecordDescription(
                min_length=68,
                max_length=68,
                format={
                    'nominal_tap_number': (21, 25),
                    'initial_tap_position': (26, 30),
                    'regulated_node_name': (31, 39),
                    'voltage_target': (40, 48),
                    'min_active_flux': (49, 57),
                    'max_active_flux': (59, 66),
                    'regulating_mode': (67, 68)
                }
            ),
            RecordDescription(
                min_length=61,
                max_length=61,
                format={
                    'tap_number': (21, 25),
                    'sending_side_voltage': (26, 34),
                    'receiving_side_voltage': (35, 43),
                    'leakage_impedance': (44, 52),
                    'phase_shift_angle': (53, 61)
                },
                list_name="taps"
            )
        ]
    ),
    EchRecordType.LOAD: NetworkDataDescription(
        max_nb_records=1,
        network_data=Load,
        record_descriptions=[
            RecordDescription(
                min_length=94,
                max_length=103,
                format={
                    'name': (3, 11),
                    'state': (12, 13),
                    'bus_name': (14, 22),
                    'active_power': (41, 49),
                    'reactive_power': (68, 76)
                }
            )
        ]
    ),
    EchRecordType.CAPACITOR_BANK: NetworkDataDescription(
        max_nb_records=1,
        network_data=CapacitorBank,
        record_descriptions=[
            RecordDescription(
                min_length=110,
                max_length=110,
                format={
                    'name': (2, 10),
                    'bus_name': (11, 19),
                    'number_active_steps': (38, 41),
                    'active_loss_on_step': (42, 50),
                    'reactive_power_on_step': (51, 59)
                }
            )
        ]
    ),
    EchRecordType.SVC: NetworkDataDescription(
        max_nb_records=1,
        network_data=StaticVarCompensator,
        record_descriptions=[
            RecordDescription(
                min_length=123,
                max_length=132,
                format={
                    'name': (3, 11),
                    'state': (12, 13),
                    'bus_name': (14, 22)
                }
            )
        ]
    ),
    EchRecordType.HVDC_CSC_CONVERTER: NetworkDataDescription(
        max_nb_records=2,
        network_data=HVDCCurrentSourceConverter,
        record_descriptions=[
            RecordDescription(
                min_length=141,
                max_length=141,
                format={
                    'name': (5, 13),
                    'bus_name': (32, 40),
                    'state': (41, 42)
                }
            ),
            # Next records are ignored
            RecordDescription(
                min_length=85,
                max_length=85,
                format={}
            )
        ]
    ),
    EchRecordType.HVDC_VSC_CONVERTER: NetworkDataDescription(
        max_nb_records=2,
        network_data=HVDCVoltageSourceConverter,
        record_descriptions=[
            RecordDescription(
                min_length=118,
                max_length=118,
                format={
                    'name': (5, 13),
                    'bus_name': (32, 40),
                    'state': (41, 42)
                }
            ),
            # Next records are ignored
            RecordDescription(
                min_length=85,
                max_length=85,
                format={}
            )
        ]
    )
}


class EchEurostagFileParser(EurostagFileParser):
    """
    Eurostag .ech file parser.
    """

    def __init__(self, file_path: str):
        """
        Initialize the object specifying the type and description of the corresponding file.

        :param file_path: Path to the .ech file to read.
        """
        # Previous record read from the file (type + number)
        self._prev_record_type: RecordType = None
        self._prev_record_nb: int = 0
        # Lengths of all the record types that may appear in the file
        self._record_type_lengths = sorted({len(e.value) for e in EchRecordType}, reverse=True)

        # Generate record types only once to increase performances
        self._record_types = {}
        for type in EchRecordType:
            self._record_types[type.value] = type

        super().__init__(
            file_type=FileType.ECH,
            file_description=ECH_FILE_DESCRIPTION,
            file_path=file_path
        )

    def _get_record_number(self, record_type: RecordType, file_line: str) -> Union[int, None]:
        """
        Determine the record number based on a record file line and the previous record number.

        :param record_type: The type of the record being added.
        :param line: The line of the file corresponding to the record.
        :return: The record number, or None if it could not be identified.
        """
        # Get record length and network data description
        data_description = self.file_description[record_type]
        record_len = len(file_line)

        if (
            record_type != self._prev_record_type or
            data_description.max_nb_records == 1 or
            self._prev_record_nb == data_description.max_nb_records
        ):
            # New type or record, data with only one record or maximum number of records reached -> new record
            record_nb = 1
        else:
            if self._prev_record_nb >= len(data_description.record_descriptions):
                # Record number higher than number of record descriptions
                last_record_desc = data_description.record_descriptions[-1]
                if record_len < last_record_desc.min_length or record_len > last_record_desc.max_length:
                    # Record is not of the same type as the last record in description
                    record_nb = 1
                else:
                    # Record number is the same as the previous record
                    record_nb = self._prev_record_nb
            else:
                # Increment record number
                record_nb = self._prev_record_nb + 1

        return record_nb

    def _identify_record(self, file_line: str) -> Union[Tuple[RecordType, int], None]:
        """
        Identify a record represented by a line from a .ech Eurostag file.

        :param file_line: A line of a .ech Eurostag file
        :return: A tuple containing the type of record and its number, if the record is of interest, otherwise None.
        """
        # Check if empty record
        if file_line == "":
            self._prev_record_nb = 0
            self._prev_record_type = None
            return None

        # Get record type, performing a longest prefix match
        record_type = None
        for i in self._record_type_lengths:
            line_rtype = file_line[0:i]
            if line_rtype in self._record_types:
                # New type or record
                record_type = self._record_types[line_rtype]
                break

        if record_type is None or record_type not in self.file_description:
            # Unknown record or record not of interest
            return None

        # Get record number
        record_nb = self._get_record_number(record_type, file_line)

        # Update record number
        self._prev_record_nb = record_nb
        self._prev_record_type = record_type

        return (record_type, record_nb)
