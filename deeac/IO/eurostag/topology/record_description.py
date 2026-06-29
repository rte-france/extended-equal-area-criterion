"""
Module for record_description.

:module: record_description
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from enum import Enum
from typing import Dict, Tuple



class RecordType(Enum):
    """
    Recordtype.
    
    Rationale:
        This class handles input parsing or configuration shaping. It converts
        external data into the explicit objects consumed by the EEAC pipeline.
    
    :summary: Class metadata.
    """
    pass


class RecordDescription:
    """
    Recorddescription.
    
    Rationale:
        This class handles input parsing or configuration shaping. It converts
        external data into the explicit objects consumed by the EEAC pipeline.
    
    :ivar format: format.
    :ivar min_length: min length.
    :ivar max_length: max length.
    :ivar list_name: list name.
    """

    def __init__(self, format: Dict[str, Tuple[int, int]], min_length: int, max_length: int, list_name: str = None):
        """
        Initilization.
        
        :param format: Expected format for a record having this description.
        :param min_length: Minimum length expected for a record having this description.
        :param max_length: Maximum length expected for a record having this description.
        :param list_name: Name of the list that will contain the reports having this description.
        """
        self.format = format
        self.min_length = min_length
        self.max_length = max_length
        self.list_name = list_name

    def parse_record(self, record: str) -> Dict[str, str]:
        """
        Parse a record according to its description.
        
        :param record: The record to parse.
        :return: A dictionary whose keys are the expected column names appearing in the format, and whose values
        are the elements identified for these columns in the record.
        :raise UnexpectedRecordLengthException if the record does not have the expected length.
        """
        # Check length
        self.raise_for_unexpected_length(record)

        parsed_record = dict()
        record_len = len(record)
        for name, (start, end) in self.format.items():
            if end > record_len:
                # Field is incomplete according to description
                if start < record_len:
                    # Field is present with blank trailing characters trimmed
                    record_field = record[start:].strip()
                else:
                    # Field is not mandatory and does not appear in record
                    parsed_record[name] = None
                    continue
            else:
                # Field is complete
                record_field = record[start:end].strip()
            if record_field == "":
                # Replace empty strings by None
                record_field = None
            parsed_record[name] = record_field
        return parsed_record

    def raise_for_unexpected_length(self, record: str):
        """
        Raise an exception if a record does not have the expected length.
        
        :param record: The record to check.
        :raise UnexpectedRecordLengthException if the specified record does not have the expected length.
        """
        record_len = len(record)
        if record_len < self.min_length or record_len > self.max_length:
            raise ValueError(
                f"Unexpected record length {record_len} (expected {self.min_length}..{self.max_length}) "
                f"for format {self.format}: {record}"
            )
