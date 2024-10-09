# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List, Dict

from deeac.domain.exceptions import DEEACException


class LoadFlowDivergenceException(DEEACException):
    """
    Exception raised when the error code ERR-019.0461 has been detected in the .lf file
    indicating a divergence of the load flow
    """

    def __str__(self) -> str:
        return "Exception code ERR-019.0461 detected in the .lf file indicating a divergence of load flow\n" \
               "No EEAC computed"


class LoadFlowDataValidationException(DEEACException):
    """
    Exception raised when a Pydantic model could not be created based on an input dictionary containing the load flow
    data.
    This error focuses on a single validation error.

    The location specifies where the error occurs. The first item in the list will be the field where the error
    occurred, and if the field is a sub-model, subsequent items will be present to indicate the nested location of the
    error.

    The category specifies a computer-readable identifier of the error category.
    """

    def __init__(self, load_flow_data: Dict, location: List[str], category: str):
        """
        Initialization.

        :param network_data_records: Records associated to the network data.
        :param location: Location of the invalid field in the record.
        :param category: Category of the error associated to the incorrect field.
        """
        self.load_flow_data = load_flow_data
        self.location = location
        self.category = category

    def __str__(self) -> str:
        return(
            f"Validation error in LoadFlowData. Error location: {self.location}, Error category: {self.category}.\n"
            f"Load flow data: {self.load_flow_data}\n"
        )


class LoadFlowTransformerException(DEEACException):
    """
    Exception raised when the sending node of a transformer is unknown in load flow results.
    """

    def __init__(self, receiving_node_name: str):
        """
        Initialization.

        :param receiving_node_name: Name of receiving node of the transformer.
        """
        self.receiving_node_name = receiving_node_name

    def __str__(self) -> str:
        return(
            f"Cannot identify sending node name associated to transformer with receiving node name "
            f"{self.receiving_node_name}"
        )
