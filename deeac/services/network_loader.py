# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.domain.ports.topology import TopologyParser
from deeac.domain.ports.load_flow import LoadFlowParser
from deeac.domain.models import Network


class NetworkLoader:
    """
    Service to load a network in the models based on a topology and a load flow parsers.
    """

    def __init__(self, topology_parser: TopologyParser, load_flow_parser: LoadFlowParser):
        """
        Initialize the network loader.

        :param topology_parser: Topology parser in charge of parsing the input network topology.
        :param load_flow_parser: Load flow parser in charge of parsing the load flow of the corresponding topology.
        """
        self.topology_parser = topology_parser
        self.load_flow_parser = load_flow_parser

    def load_network(self) -> Network:
        """
        Load a network.

        :return: The network loaded based on the topology and load flow data.
        """
        # Parse network topology and load flow data
        network_topology = self.topology_parser.parse_network_topology()
        load_flow = self.load_flow_parser.parse_load_flow()

        # Create the network based on a network topology and load flow data
        return Network.create_network(network_topology, load_flow)
