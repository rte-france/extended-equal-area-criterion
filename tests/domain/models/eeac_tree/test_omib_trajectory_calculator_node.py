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
from deeac.domain.models.rotor_angle_trajectory_calculator.taylor_series import OMIBTaylorSeries
from deeac.domain.models.eeac_tree import (
    EACNodeInputs, EEACTreeNodeIOType, OMIBTrajectoryCalculatorNode, OMIBTrajectoryCalculatorNodeInputs,
    OMIBTrajectoryCalculatorNodeOutputs
)
from deeac.domain.models.omib import OMIBSwingState, OMIBStabilityState
import deeac.domain.ports.dtos.eeac_tree as node_dtos


class TestOMIBTrajectoryCalculatorNode:

    def test_select_cluster(self, case1_omib_traj_calc_tree_node):
        assert case1_omib_traj_calc_tree_node.expected_inputs_dto_type == OMIBTrajectoryCalculatorNodeInputs

    def test_inputs(self, case1_omib_traj_calc_tree_node, case1_zoomib):
        # Valid inputs
        inputs = OMIBTrajectoryCalculatorNodeInputs(
            critical_angle=1,
            maximum_angle=6,
            omib=case1_zoomib
        )
        case1_omib_traj_calc_tree_node.inputs = inputs
        assert case1_omib_traj_calc_tree_node.inputs == inputs

        # Invalid inputs
        with pytest.raises(EEACTreeNodeInputsException):
            case1_omib_traj_calc_tree_node.inputs = EACNodeInputs(omib=case1_zoomib)

    def test_verify_input_types(self, case1_omib_traj_calc_tree_node):
        assert case1_omib_traj_calc_tree_node.input_types == {
            EEACTreeNodeIOType.CRIT_ANGLE,
            EEACTreeNodeIOType.MAX_ANGLE,
            EEACTreeNodeIOType.OMIB,
            EEACTreeNodeIOType.OUTPUT_DIR
        }

    def test_verify_output_types(self, case1_omib_traj_calc_tree_node):
        assert case1_omib_traj_calc_tree_node.output_types == {EEACTreeNodeIOType.CLUSTER_RESULTS}

    def test_can_be_leaf(self, case1_omib_traj_calc_tree_node):
        assert case1_omib_traj_calc_tree_node.can_be_leaf()

    def test_run(self, case1_omib_traj_calc_tree_node):
        # Run and check outputs
        case1_omib_traj_calc_tree_node.run()

        outputs = case1_omib_traj_calc_tree_node.outputs
        assert type(outputs) == OMIBTrajectoryCalculatorNodeOutputs
        assert cmath.isclose(outputs.cluster_results.critical_angle, 1.2, abs_tol=10e-9)
        assert cmath.isclose(outputs.cluster_results.maximum_angle, 6.3, abs_tol=10e-9)
        assert cmath.isclose(outputs.cluster_results.critical_time, 0.26714896618180484, abs_tol=10e-9)
        assert cmath.isclose(outputs.cluster_results.maximum_time, 0.706991450604408, abs_tol=10e-9)
        assert outputs.cluster_results.omib_stability_state == OMIBStabilityState.POTENTIALLY_STABLE
        assert outputs.cluster_results.omib_swing_state == OMIBSwingState.FORWARD
        assert {gen.name for gen in outputs.cluster_results.critical_cluster.generators} == {"GENA1"}
        assert {gen.name for gen in outputs.cluster_results.non_critical_cluster.generators} == {
            "GENB1", "GENB2", "NHVCEQ"
        }

    def test_generate_report(self, case1_omib_traj_calc_tree_node):
        case1_omib_traj_calc_tree_node.run()
        report = re.sub(
            "\tExecution time: \\d+\\.\\d+ seconds\n",
            "",
            case1_omib_traj_calc_tree_node._generate_report()
        )
        assert report == (
            "Report for node 6_DOMIB Trajectory Calculator:\n"
            "\tConfiguration:\n"
            "\t\tType of calculator: OMIBTaylorSeries\n"
            "\t\tCritical angle shift: 2.0 deg\n"
            "\tInputs:\n"
            "\t\tCritical angle: 1.2 rad [68.755 deg]\n"
            "\t\tMaximum angle: 6.3 rad [360.963 deg]\n"
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
            "\tOutputs:\n"
            "\t\tGenerators: GENA1, GENB1, GENB2, NHVCEQ\n"
            "\t\tCritical cluster: GENA1\n"
            "\t\tCritical angle: 1.2 rad [68.755 deg]\n"
            "\t\tCritical time: 267.149 ms\n"
            "\t\tMaximum angle: 6.3 rad [360.963 deg]\n"
            "\t\tMaximum time: 706.991 ms\n"
            "\t\tOMIB stability state: POTENTIALLY STABLE\n"
            "\t\tOMIB swing state: FORWARD"
        )

    def test_create_node(self):
        config = node_dtos.OMIBTrajectoryCalculatorConfiguration(
            calculator_type=node_dtos.OMIBTrajectoryCalculatorType.TAYLOR,
            critical_angle_shift=1
        )
        node_data = node_dtos.EEACTreeNode(
            name="test-node",
            id=1,
            type=node_dtos.EEACTreeNodeType.OMIB_TRAJECTORY_CALCULATOR,
            configuration=config
        )
        node = OMIBTrajectoryCalculatorNode.create_node(node_data)
        assert type(node) == OMIBTrajectoryCalculatorNode
        assert node._id == 1
        assert node._name == "test-node"
        assert node._calculator_type == OMIBTaylorSeries
        assert node._critical_angle_shift == 1
        assert not node.must_display_report
