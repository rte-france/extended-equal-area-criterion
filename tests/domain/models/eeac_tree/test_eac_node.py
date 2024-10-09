# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest
import cmath
import re

from deeac.domain.exceptions import EEACTreeNodeInputsException
from deeac.domain.models.eeac_tree import OMIBNodeInputs, EACNodeInputs, EACNodeOutputs, EEACTreeNodeIOType, EACNode
import deeac.domain.ports.dtos.eeac_tree as node_dtos


class TestEACNode:

    def test_select_cluster(self, case1_eac_tree_node):
        assert case1_eac_tree_node.expected_inputs_dto_type == EACNodeInputs

    def test_inputs(self, case1_eac_tree_node, case1_zoomib, case1_network_line_fault):
        # Valid inputs
        inputs = EACNodeInputs(omib=case1_zoomib)
        case1_eac_tree_node.inputs = inputs
        assert case1_eac_tree_node.inputs == inputs

        # Invalid inputs
        with pytest.raises(EEACTreeNodeInputsException):
            case1_eac_tree_node.inputs = OMIBNodeInputs(
                network=case1_network_line_fault,
                critical_cluster=case1_zoomib.critical_cluster,
                non_critical_cluster=case1_zoomib.non_critical_cluster
            )

    def test_verify_input_types(self, case1_eac_tree_node):
        assert case1_eac_tree_node.input_types == {
            EEACTreeNodeIOType.OMIB,
            EEACTreeNodeIOType.OUTPUT_DIR
        }

    def test_verify_output_types(self, case1_eac_tree_node):
        assert case1_eac_tree_node.output_types == {
            EEACTreeNodeIOType.OMIB,
            EEACTreeNodeIOType.CRIT_ANGLE,
            EEACTreeNodeIOType.MAX_ANGLE
        }

    def test_can_be_leaf(self, case1_eac_tree_node):
        assert not case1_eac_tree_node.can_be_leaf()

    def test_run(self, case1_eac_tree_node, case1_zoomib, case1_line_fault_zoomib_eac):
        # Run and check outputs
        case1_eac_tree_node.run()

        outputs = case1_eac_tree_node.outputs
        assert type(outputs) == EACNodeOutputs
        assert outputs.omib == case1_zoomib
        assert cmath.isclose(outputs.critical_angle, case1_line_fault_zoomib_eac.critical_clearing_angle, abs_tol=10e-9)
        assert cmath.isclose(outputs.maximum_angle, case1_line_fault_zoomib_eac.maximum_angle, abs_tol=10e-9)

    def test_generate_report(self, case1_eac_tree_node):
        case1_eac_tree_node.run()
        report = re.sub("\tExecution time: \\d+\\.\\d+ seconds\n", "", case1_eac_tree_node._generate_report())
        assert report == (
            "Report for node 5_DOMIB EAC:\n"
            "\tConfiguration:\n"
            "\t\tAngle increment: 1.8 deg\n"
            "\t\tMaximum OMIB integration angle: 360.0 deg\n"
            "\tOutputs:\n"
            "\t\tCritical angle: 1.201 rad [68.826 deg]\n"
            "\t\tMaximum angle: 2.238 rad [128.226 deg]\n"
            "\t\tOMIB:\n"
            "\t\t\tType: ZOOMIB\n"
            "\t\t\tStability state: POTENTIALLY STABLE\n"
            "\t\t\tSwing state: FORWARD\n"
            "\t\t\tCritical generators: GENA1\n"
            "\t\t\tProperties:\n"
            "\t\t\t\tPRE-FAULT:\n"
            "\t\t\t\t\tAngle: 0.039 rad [2.226 deg] - Time: 0 ms - Angle shift: -0.365 "
            "rad [-20.909 deg] - Constant power: 2.883 p.u. - Maximum power: 14.896 p.u.\n"
            "\t\t\t\tDURING-FAULT:\n"
            "\t\t\t\t\tAngle: 0.039 rad [2.226 deg] - Time: 0 ms - Angle shift: -0.21 rad "
            "[-12.005 deg] - Constant power: 1.326 p.u. - Maximum power: 4.228 p.u.\n"
            "\t\t\t\tPOST-FAULT:\n"
            "\t\t\t\t\tAngle: 0.039 rad [2.226 deg] - Time: 0 ms - Angle shift: -0.392 "
            "rad [-22.455 deg] - Constant power: 3.71 p.u. - Maximum power: 12.269 p.u.\n"
        )

    def test_create_node(self):
        config = node_dtos.EACConfiguration(angle_increment=1.8, maximum_integration_angle=360)
        node_data = node_dtos.EEACTreeNode(
            name="test-node",
            id=1,
            type=node_dtos.EEACTreeNodeType.EAC,
            configuration=config
        )
        node = EACNode.create_node(node_data)
        assert type(node) == EACNode
        assert node._id == 1
        assert node._name == "test-node"
        assert cmath.isclose(node._angle_increment, 1.8, abs_tol=10e-9)
        assert cmath.isclose(node._max_integration_angle, 360, abs_tol=10e-9)
        assert not node.must_display_report
