# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.domain.ports.dtos.eeac_tree import EEACTree
from abc import ABC, abstractmethod


class EEACTreeParser(ABC):
    """
    Abstract class gathering methods to read an EEAC execution tree from an input file.
    """

    @abstractmethod
    def parse_execution_tree(self) -> EEACTree:
        """
        Parse a execution tree input to retrieve its content.

        :return: An object representing the parsed execution tree.
        """
        pass
