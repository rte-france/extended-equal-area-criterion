# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from abc import ABC, abstractmethod

from deeac.domain.ports.dtos.load_flow import LoadFlowResults


class LoadFlowParser(ABC):
    """
    Abstract class gathering methods to parse the results of a load flow analysis.
    """

    @abstractmethod
    def parse_load_flow(self) -> LoadFlowResults:
        """
        Parse the results of a load flow analysis.

        :return: The load flow results.
        """
        pass
