# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List

from deeac.domain.exceptions import DEEACException


class JSONParsingException(DEEACException):
    """
    Exception raised when a JSON file could not be parsed
    """

    def __init__(self, msg: str, column: int, row: int):
        """
        Initialization.

        :param msg: Description of the error.
        :param column: Column number where the error is identified.
        :param row: Row number where the error is identified.
        """
        self.msg = msg
        self.column = column
        self.row = row

    def __str__(self) -> str:
        return f"JSON Parsing error at line {self.row} and column {self.column}: {self.msg}\n"


class EACTreeDataValidationException(DEEACException):
    """
    Exception raised when a Pydantic model could not be created based on an input dictionary containing the tree data.
    This error focuses on a single validation error.

    The location specifies where the error occurs. The first item in the list will be the field where the error
    occurred, and if the field is a sub-model, subsequent items will be present to indicate the nested location of the
    error.

    The category specifies a computer-readable identifier of the error category.
    """

    def __init__(self, location: List[str], category: str):
        """
        Initialization.

        :param location: Location of the invalid field in the record.
        :param category: Category of the error associated to the incorrect field.
        """
        self.location = location
        self.category = category

    def __str__(self) -> str:
        return(
            f"Validation error in EEAC tree data. Error location: {self.location}, Error category: {self.category}.\n"
        )
