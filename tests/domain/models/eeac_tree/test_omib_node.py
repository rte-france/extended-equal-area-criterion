# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest
import re

from deeac.domain.exceptions import EEACTreeNodeInputsException
from deeac.domain.models.eeac_tree import OMIBNodeInputs, EACNodeInputs, EEACTreeNodeIOType, OMIBNodeOutputs, OMIBNode
from deeac.domain.models.omib import DOMIB, ZOOMIB
import deeac.domain.ports.dtos.eeac_tree as node_dtos


class TestOMIBNode:

    def test_select_cluster(self, case1_omib_tree_node):
        assert case1_omib_tree_node.expected_inputs_dto_type == OMIBNodeInputs

    def test_inputs(self, case1_omib_tree_node, case1_zoomib, case1_network_line_fault):
        # Valid inputs
        inputs = OMIBNodeInputs(
            network=case1_network_line_fault,
            critical_cluster=case1_zoomib.critical_cluster,
            non_critical_cluster=case1_zoomib.non_critical_cluster
        )
        case1_omib_tree_node.inputs = inputs
        assert case1_omib_tree_node.inputs == inputs

        # Invalid inputs
        with pytest.raises(EEACTreeNodeInputsException):
            case1_omib_tree_node.inputs = EACNodeInputs(omib=case1_zoomib)

    def test_verify_input_types(self, case1_omib_tree_node):
        assert case1_omib_tree_node.input_types == {
            EEACTreeNodeIOType.NETWORK,
            EEACTreeNodeIOType.CRIT_CLUSTER,
            EEACTreeNodeIOType.NON_CRIT_CLUSTER,
            EEACTreeNodeIOType.OUTPUT_DIR
        }

    def test_verify_output_types(self, case1_omib_tree_node):
        assert case1_omib_tree_node.output_types == {EEACTreeNodeIOType.OMIB}

    def test_can_be_leaf(self, case1_omib_tree_node):
        assert not case1_omib_tree_node.can_be_leaf()

    def test_run(self, case1_omib_tree_node):
        # Run and check outputs
        case1_omib_tree_node.run()

        outputs = case1_omib_tree_node.outputs
        assert type(outputs) == OMIBNodeOutputs
        omib = outputs.omib
        assert type(omib) == DOMIB

    def test_generate_report(self, case1_omib_tree_node):
        case1_omib_tree_node.run()
        report = re.sub("\tExecution time: \\d+\\.\\d+ seconds\n", "", case1_omib_tree_node._generate_report())
        assert report == (
            "Report for node 4_DOMIB:\n"
            "\tConfiguration:\n"
            "\t\tType of OMIB: DOMIB\n"
            "\tOutput:\n"
            "\t\tOMIB:\n"
            "\t\t\tType: DOMIB\n"
            "\t\t\tStability state: UNKNOWN\n"
            "\t\t\tSwing state: FORWARD\n"
            "\t\t\tCritical generators: GENA1\n"
            "\t\t\tProperties:\n"
            "\t\t\t\tPRE-FAULT:\n"
            "\t\t\t\t\tAngle: 0.044 rad [2.516 deg] - Time: 0 ms - Angle shift: -0.36 rad "
            "[-20.614 deg] - Constant power: 2.883 p.u. - Maximum power: 14.899 p.u.\n"
            "\t\t\t\tDURING-FAULT:\n"
            "\t\t\t\t\tAngle: 0.044 rad [2.516 deg] - Time: 0 ms - Angle shift: -0.207 "
            "rad [-11.888 deg] - Constant power: 1.326 p.u. - Maximum power: 4.229 p.u.\n"
            "\t\t\t\tPOST-FAULT:\n"
            "\t\t\t\t\tAngle: 0.044 rad [2.516 deg] - Time: 0 ms - Angle shift: -0.388 "
            "rad [-22.229 deg] - Constant power: 3.71 p.u. - Maximum power: 12.274 p.u."
        )

    def test_create_node(self):
        config = node_dtos.OMIBConfiguration(omib_type=node_dtos.OMIBType.ZOOMIB)
        node_data = node_dtos.EEACTreeNode(
            name="test-node",
            id=1,
            type=node_dtos.EEACTreeNodeType.OMIB,
            configuration=config
        )
        node = OMIBNode.create_node(node_data)
        assert type(node) == OMIBNode
        assert node._id == 1
        assert node._name == "test-node"
        assert node._omib_type == ZOOMIB
        assert not node.must_display_report
