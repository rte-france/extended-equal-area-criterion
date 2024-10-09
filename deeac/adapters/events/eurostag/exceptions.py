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


class EventDataValidationException(DEEACException):
    """
    Exception raised when a Pydantic model could not be created based on an input dictionary containing the event data.
    This error focuses on a single validation error.

    The location specifies where the error occurs. The first item in the list will be the field where the error
    occurred, and if the field is a sub-model, subsequent items will be present to indicate the nested location of the
    error.

    The category specifies a computer-readable identifier of the error category.
    """

    def __init__(self, event_record: str, location: List[str], category: str):
        """
        Initialization.

        :param event_record: Event record associated to the event data.
        :param location: Location of the invalid field in the record.
        :param category: Category of the error associated to the incorrect field.
        """
        self.event_record = event_record
        self.location = location
        self.category = category

    def __str__(self) -> str:
        return(
            f"Validation error in EventData. Error location: {self.location}, Error category: {self.category}.\n"
            f"Record: {self.event_record}\n"
        )
