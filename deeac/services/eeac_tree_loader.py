# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.domain.ports.eeac_tree import EEACTreeParser
from deeac.domain.models.eeac_tree import EEACTree


class EEACTreeLoader:
    """
    Service to load an EEAC execution tree in the models based on an tree parser.
    """

    def __init__(self, tree_parser: EEACTreeParser):
        """
        Initialize the event loader.

        :param tree_parser: Execution tree parser in charge of parsing the input events.
        """
        self.tree_parser = tree_parser

    def load_eeac_tree(self) -> EEACTree:
        """
        Load the EEAC execution tree.

        :return: The EEAC execution tree.
        """
        # Parse tree data
        tree_data = self.tree_parser.parse_execution_tree()

        # Create the model based the parsed data
        return EEACTree.create_tree(tree_data)
