# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List, Dict, Tuple

from deeac.domain.exceptions import DEEACException


class UnexpectedRecordLengthException(DEEACException):
    """
    Exception raised when a record in an Eurostag file does not have the excpected length.
    """

    def __init__(
        self, record: str, record_len: int, expected_min_record_len: int, expected_max_record_len: int,
        expected_record_format: Dict[str, Tuple[int, int]], file_line_nb: int = None
    ):
        """
        Initialize the exception.

        :param record: Record that caused the exception (as a string).
        :param record_len: Length of the record that caused the exception.
        :param expected_min_record_len: Expected minimum length of the record.
        :param expected_max_record_len: Expected maximum length of the record.
        :param expected_record_format: Expected record format.
        :param file_line_nb: Line of the file where where the reccord was found.
        """
        self.record = record
        self.record_len = record_len
        self.expected_min_record_len = expected_min_record_len
        self.expected_max_record_len = expected_max_record_len
        self.expected_record_format = expected_record_format
        self.file_line_nb = file_line_nb

    def __str__(self) -> str:
        file_line_nb_str = f" at line {self.file_line_nb} in the input file" if self.file_line_nb is not None else ""
        return(
            f"Unexpected length observed for record{file_line_nb_str}.\n"
            f"Record: {self.record}\n"
            f"Record length: {self.record_len} characters\n"
            f"Expected minimum record length: {self.expected_min_record_len} characters\n"
            f"Expected maximum record length: {self.expected_max_record_len} characters\n"
            f"Expected record format: {self.expected_record_format}\n"
        )


class IncompleteNetworkDataException(DEEACException):
    """
    Exception raised when the number of records is not correct for network data.
    """

    def __init__(self, network_data_records: List[str], nb_records: int, nb_descriptions: int, max_nb_records: int):
        """
        Initialization.

        :param network_data_records: Records associated to the incomplete network data.
        :param nb_records: Number of records observed for the incomplete network data.s
        :param nb_descriptions: Number of record descriptions assocciated to the description of the incomplete network
                                data.
        :param max_nb_records: Maximum number of records allowed for this type of network data.
        """
        self.network_data_records = network_data_records
        self.nb_records = nb_records
        self.nb_descriptions = nb_descriptions
        self.max_nb_records = max_nb_records

    def __str__(self) -> str:
        if self.max_nb_records == -1:
            max_nb_records_str = "Unbounded"
        else:
            max_nb_records_str = str(self.max_nb_records)
        records = "\n".join(self.network_data_records)
        return(
            f"Incomplete network data:\n"
            f"Number of records: {self.nb_records}\n"
            f"Expected minimum number of records: {self.nb_descriptions}.\n"
            f"Expected maximum number of records: {max_nb_records_str}.\n"
            f"Observed records: {records}\n"
        )


class NetworkDataValidationException(DEEACException):
    """
    Exception raised when a Pydantic model could not be created based on an input dictionary containing the records
    of network data.
    This error focuses on a single validation error.

    The location specifies where the error occurs. The first item in the list will be the field where the error
    occurred, and if the field is a sub-model, subsequent items will be present to indicate the nested location of the
    error.

    The category specifies a computer-readable identifier of the error category.
    """

    def __init__(self, network_data_records: List[str], location: List[str], category: str):
        """
        Initialization.

        :param network_data_records: Records associated to the network data.
        :param location: Location of the invalid field in the record.
        :param category: Category of the error associated to the incorrect field.
        """
        self.network_data_records = network_data_records
        self.location = location
        self.category = category

    def __str__(self) -> str:
        records = "\n".join(self.network_data_records)
        return(
            f"Validation error in NetworkData. Error location: {self.location}, Error category: {self.category}.\n"
            f"Records: {records}\n"
        )


class GeneralParametersException(DEEACException):
    """
    Exception raised when multiple records forr general parameters appear in the Eurostag ECH file.
    """

    def __str__(self) -> str:
        return "Multiple records for general parameters appear in the input ECH file."
