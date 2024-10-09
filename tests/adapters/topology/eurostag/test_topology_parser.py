# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest

from deeac.domain.exceptions import DEEACExceptionList
from deeac.domain.ports.exceptions import (
    NetworkElementNameException, BranchParallelException, TapNumberException
)
from deeac.adapters.topology.eurostag.exceptions import GeneralParametersException
from tests.adapters.dto_comparators import dtos_are_equal


class TestTopologyParser:

    def test_parse_network_topology(
        self, topology_parser, topology_parser_base_power_errors, topology_parser_bus_errors, topology_parser_errors,
        complete_case_topology
    ):
        # Parse complete case
        topology = topology_parser.parse_network_topology()
        assert dtos_are_equal(topology, complete_case_topology)

        # Parse with base power errors
        with pytest.raises(DEEACExceptionList) as e:
            topology_parser_base_power_errors.parse_network_topology()
        assert len(e.value.exceptions) == 1
        assert isinstance(e.value.exceptions[0], GeneralParametersException)

        # Parse with multiple slack bus
        with pytest.raises(DEEACExceptionList) as e:
            topology_parser_bus_errors.parse_network_topology()
        assert len(e.value.exceptions) == 2
        assert isinstance(e.value.exceptions[0], NetworkElementNameException)
        assert e.value.exceptions[0].name == "NHVA4"
        assert isinstance(e.value.exceptions[1], NetworkElementNameException)
        assert e.value.exceptions[1].name == "NHVCEQ"

        # Parse with other errors
        with pytest.raises(DEEACExceptionList) as e:
            topology_parser_errors.parse_network_topology()
        assert len(e.value.exceptions) == 3
        assert isinstance(e.value.exceptions[0], BranchParallelException)
        assert e.value.exceptions[0].sending_bus == "NHVC2"
        assert e.value.exceptions[0].receiving_bus == "NHVB1"
        assert e.value.exceptions[0].parallel_id == "2"
        assert isinstance(e.value.exceptions[1], NetworkElementNameException)
        assert e.value.exceptions[1].name == "LOAD"
        assert isinstance(e.value.exceptions[2], NetworkElementNameException)
        assert e.value.exceptions[2].name == "GEN A1"
