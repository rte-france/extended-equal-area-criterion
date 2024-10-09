# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import re
from enum import Enum
from typing import List, Dict, Tuple
from pydantic import ValidationError
from collections import defaultdict

from deeac.adapters.load_flow.eurostag.dtos import LoadFlowData
from deeac.domain.exceptions import DEEACExceptionList
from .exceptions import LoadFlowDataValidationException


# Delimiters of the tables
LOAD_FLOW_TABLE_DELIMITER = "--"
LOAD_FLOW_TABLE_COLUMN_DELIMITER = "|"

# Pattern in the table to consider as None values (in addition to empty string)
LOAD_FLOW_NONE_PATTERN = "/"


class TableType(Enum):
    """
    Types of the table in the Eurostag load flow results
    """
    TRANSFORMERS = "TRANSFORMERS"
    HVDC_CONVERTERS_RESULTS = "HVDC_CONVERTERS_RESULTS"
    RESULTS = "RESULTS"
    TRANSFORMERSNODEDATA = "TRANSFORMERSNODEDATA"
    TRANSFORMERTAPDATA = "TRANSFORMERTAPDATA"


class TableDescription:
    """
    Description of a table in the load flow file.

    The format of a row is a dictionary associating a field name to a tuple.
    The first element in the tuple is the column number.
    The second is the number of characters allocated in the table for the field, may be -1 if unbounded.
    The last element is the position of the field in the column. Its meaning varies according two the previous element
    in the tuple:
        1. It corresponds to the subcolumn number if the length of the field is unbounded (assume blank separator
           between subcolumns).
        2. It corresponds to the position of the field in the column if its length is bounded and provided.
        3. If not specified, the column is assumed to contain only one field
    """

    def __init__(
        self, names: List[str], first_data_row_nb: int, row_format: Dict[str, Tuple], load_flow_data: LoadFlowData,
        data_occurences: Tuple = (1, 0), strict_match_names: bool = True
    ):
        """
        Initialization

        :param names: Possible names of the table.
        :param first_data_row_nb: Number of the first row containing data (allows to skip headers).
        :param row_format: Format of a data row in the table.
        :param load_flow_data: Object to which the row data must be mapped.
        :param data_occurences: Tuple describing if multiple occurrences of the data may appear in the row.
                                The first element of the tuple is the number of occurences, and the second is the
                                offset in terms of columns between two instances of a field.
        :param strict_match_names: True if the names of the table must be strictly matched, i.e. the table name found
                                   in the load flow file must striclty be one of the provided names. If False, one of
                                   the provided names must be found in the table name.
                                   E.g. Provided name "TABLE 1" with strict_match_names set to False matches
                                   "TABLE 1 SVC" or "RESULTS TABLE 1". It does not match if strict_match_names is set
                                   to True.
        """
        self.names = names
        self.first_data_row_nb = first_data_row_nb
        self.row_format = row_format
        self.load_flow_data = load_flow_data
        self.data_occurences = data_occurences
        names = "|".join([re.escape(name) for name in self.names])
        if strict_match_names:
            self.pattern = re.compile(f"(?:^.*\\|[\\s]*({names})[\\s]*\\|.*$|^({names})$)")
        else:
            self.pattern = re.compile(f"{names}")

        # Arrange row format according to the columns
        self._single_field_columns = {}
        self._unbounded_length_field_columns = defaultdict(list)
        self._fixed_length_field_columns = defaultdict(list)
        for (field_name, (column_nb, field_len, field_position)) in self.row_format.items():
            if field_position is None:
                # Single field
                self._single_field_columns[column_nb] = field_name
            elif field_len == -1:
                # Unbounded-length fields
                self._unbounded_length_field_columns[column_nb].append((field_name, field_position))
            else:
                # Fixed-length fields
                self._fixed_length_field_columns[column_nb].append((field_name, field_len, field_position))

    def _add_field_data(self, load_flow_data_content: Dict[str, str], field_name: str, field_data: str):
        """
        Add field data to load flow data.

        :param load_flow_data_content: Data of the load flow to which the field must be added.
        :param field_name: Name of the field.
        :param field_data: Data of the field.
        """
        if field_data == "" or field_data.startswith(LOAD_FLOW_NONE_PATTERN):
            # Nothing to add
            return
        load_flow_data_content[field_name] = field_data

    def parse_row(self, row: str) -> List[LoadFlowData]:
        """
        Parse a row into a list of load flow data objects.
        Most of the time, the list will contain only one element.

        param row: The row to parse.
        """
        # Get columns
        columns = row.split(LOAD_FLOW_TABLE_COLUMN_DELIMITER)

        # Search for each field specified in the format
        load_flow_data_objects = []
        (nb_occurences, offset) = self.data_occurences
        for i in range(0, nb_occurences):
            load_flow_data_content = {}

            # Columns with single field
            for (column_nb, field_name) in self._single_field_columns.items():
                column_nb += i * offset
                field_data = columns[column_nb].strip()
                self._add_field_data(load_flow_data_content, field_name, field_data)

            # Columns with fixed-length fields
            for (column_nb, fields) in self._fixed_length_field_columns.items():
                column_nb += i * offset
                column_content = columns[column_nb]
                for (field_name, field_len, field_position) in fields:
                    field_data = column_content[field_position:field_position + field_len].strip()
                    self._add_field_data(load_flow_data_content, field_name, field_data)

            # Columns with unbounded-length fields
            for (column_nb, fields) in self._unbounded_length_field_columns.items():
                column_nb += i * offset
                column_content = columns[column_nb].split()
                for (field_name, field_position) in fields:
                    try:
                        field_data = column_content[field_position]
                    except IndexError:
                        continue
                    self._add_field_data(load_flow_data_content, field_name, field_data)

            # Map to the load flow data object
            try:
                if not load_flow_data_content:
                    # No data
                    continue
                load_flow_data_objects.append(self.load_flow_data(**load_flow_data_content))
            except ValidationError as e:
                exception_list = DEEACExceptionList([])
                # Get validation errors and create corresponding DEEAC exceptions
                for val_error in e.errors():
                    exception_list.append(
                        LoadFlowDataValidationException(load_flow_data_content, val_error["loc"], val_error["type"])
                    )
                raise(exception_list)
        return load_flow_data_objects
