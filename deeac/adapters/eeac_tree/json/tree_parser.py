# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import json
from json.decoder import JSONDecodeError
from pydantic import ValidationError

from deeac.domain.ports.dtos.eeac_tree import EEACTree
from deeac.domain.ports.eeac_tree import EEACTreeParser
from deeac.domain.exceptions import DEEACExceptionCollector, DEEACExceptionList
from .exceptions import JSONParsingException, EACTreeDataValidationException


class JSONTreeParser(EEACTreeParser):
    """
    Parse an EEAC execution tree in the JSON format.
    """

    def __init__(self, file_path: str = None, tree_data: str = None):
        """
        Initialize the parser.

        :param file_path: File containing the EEAC tree data.
        :param tree_data: Loaded content of the EEAC tree data
        """
        if file_path is None and tree_data is None:
            raise ValueError("Specify either a json path of a tree or the tree data itself in the tree parser")
        self.file_path = file_path
        self.tree_data = tree_data

    def parse_execution_tree(self) -> EEACTree:
        """
        Parse the execution tree input to retrieve its content.

        :return: An object representing the parsed execution tree.
        """
        exception_collector = DEEACExceptionCollector()
        with exception_collector:
            if self.file_path is not None:
                try:
                    # Parse file
                    json_file = open(self.file_path)
                    tree_data = json.load(json_file)
                except JSONDecodeError as e:
                    raise JSONParsingException(e.msg, e.colno, e.lineno)
            else:
                tree_data = self.tree_data

            try:
                # Read EEAC tree
                tree = EEACTree(**tree_data)
            except ValidationError as e:
                exception_list = DEEACExceptionList()
                # Get validation errors and create corresponding DEEAC exceptions
                for val_error in e.errors():
                    exception_list.append(
                        EACTreeDataValidationException(val_error["loc"], val_error["type"])
                    )
                raise exception_list

        # Raise if any exception or return tree
        exception_collector.raise_for_exception()
        return tree
