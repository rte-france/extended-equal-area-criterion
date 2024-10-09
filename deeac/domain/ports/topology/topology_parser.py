# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.domain.ports.dtos.topology import NetworkTopology
from abc import ABC, abstractmethod


class TopologyParser(ABC):
    """
    Abstract class gathering methods to read a network topology from input files.
    """

    @abstractmethod
    def parse_network_topology(self) -> NetworkTopology:
        """
        Parse a network topology input to retrieve its elements.

        :return: An object representing the parsed network topology.
        """
        pass
