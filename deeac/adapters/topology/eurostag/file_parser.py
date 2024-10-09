# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from collections import defaultdict
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Tuple, Union, DefaultDict

from .dtos import NetworkData
from .network_data_description import NetworkDataDescription
from .record_description import RecordType
from deeac.domain.exceptions import DEEACExceptionCollector


class FileType(Enum):
    """
    Supported types of Eurostag files.
    """
    ECH = "ech"
    DTA = "dta"


class EurostagFileParser(ABC):
    """
    Parser for Eurostag topology files.
    The parser is able to read a file content only if a description of the input file is specified.
    A file description must describe all the records of interest (RecordDescription). A record corresponds to a line
    of the file. A record descripton contains the length of the record (number of characters), as well as its format.
    Multiple records may be used to represent the data of a network element (NetworkData). In this case,
    they are all of the same type (record type), and they can be distinguished based on their number (record number).
    Multiple records associated to a network element may thus have the same record number. The list of record
    descriptions for the data of a network element form a NetworkDataDescription. Their position in this list is their
    record number (starting with 1). If some network data in the file to parse contains more records than the number of
    record descriptions in the corresponding NetworkDataDescription, the last records are considered to have the same
    format as the last record description in the NetworkDataDescription.

    Once the records have been parsed, they are stored in the form of a NetworkData in a dedicated dictionary.
    The parsing of a network data is performed only if this kind of data is requested to the parser.
    """

    def __init__(self, file_type: FileType, file_description: Dict[RecordType, NetworkDataDescription], file_path: str):
        """
        Initialize the parser

        :param file_type: Type of the files that can be parsed by this parser.
        :param file_description: Description of the files that can be parsed.
        :param file_path: Path to the file to parse.
        """
        self.file_type = file_type
        self.file_description = file_description
        self.file_path = file_path

        # Records and corresponding network data
        self._file_records: DefaultDict[RecordType, List[List[str]]] = defaultdict(list)
        self._file_network_data: DefaultDict[RecordType, List[NetworkData]] = defaultdict(list)

        # Exception collector
        self._exception_collector: DEEACExceptionCollector = DEEACExceptionCollector()

    @abstractmethod
    def _identify_record(self, file_line: str) -> Union[Tuple[RecordType, int], None]:
        """
        Identify a record represented by a line from an Eurostag file.

        :param file_line: A line of an Eurostag file
        :return: A tuple containing the type of record and its number, if recognized, otherwise None.
        """
        pass

    def _add_record(self, file_line: str):
        """
        Add a record to the list of records.

        :param file_line: A line of an Eurostag file corresponding to a record.
        """
        # Get record type associated to the line
        record_info = self._identify_record(file_line)
        if record_info is None:
            # Not a record of interest
            return
        (record_type, record_nb) = record_info

        # Store record
        if record_nb == 1:
            # Add first record of new network data
            self._file_records[record_type].append([file_line])
        else:
            # Update list of records for last network data
            self._file_records[record_type][-1].append(file_line)

    def _reset_parser(self):
        """
        Reset parser so that it can read a new file.
        """
        self._file_records.clear()
        self._file_network_data = defaultdict(list)
        self._exception_collector.reset()

    def _parse_network_data(self):
        """
        Get the network data in the input file associated to a given record type.
        The file must have been read before proceeding.
        """
        if not self._file_records:
            # No record found in the file
            return

        for record_type in self._file_records:
            for network_data_records in self._file_records[record_type]:
                with self._exception_collector:
                    # Map records data to NetworkData object
                    network_data = self.file_description[record_type].parse_network_data(network_data_records)
                    self._file_network_data[record_type].append(network_data)

    def parse_file(self):
        """
        Read the records from the input file and parse the corresponding network data.

        :raise DEEACExceptionList if exceptions were observed during file parsing.
        """
        # Initialize or reset parser
        self._reset_parser()

        # Read file records
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    file_line = line.rstrip("\n")
                    self._add_record(file_line)
        except UnicodeDecodeError:
            with open(self.file_path, 'r', encoding='latin-1') as file:
                for line in file:
                    file_line = line.rstrip("\n")
                    self._add_record(file_line)

        # Check if errors were observed during file reading
        self._exception_collector.raise_for_exception()

        # Parse network data
        self._parse_network_data()

        # Check if parsing errors
        self._exception_collector.raise_for_exception()

    def get_network_data(self, record_type: RecordType) -> List[NetworkData]:
        """
        Get the network data of a given type read from the input file.

        :param record_type: The type of record associated to the network data to extract.
        :return: The list of NetworkData objects associated to the specified type of record.
        """
        return self._file_network_data[record_type]
