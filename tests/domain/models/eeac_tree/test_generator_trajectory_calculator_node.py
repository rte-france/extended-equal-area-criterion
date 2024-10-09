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
import cmath

from deeac.domain.exceptions import EEACTreeNodeInputsException
from deeac.domain.models.eeac_tree import (
    EACNodeInputs, EEACTreeNodeIOType, GeneratorTrajectoryCalculatorNode, EEACClusterResults,
    GeneratorTrajectoryCalculatorNodeInputs, GeneratorTrajectoryCalculatorNodeOutputs
)
from deeac.domain.models.omib import OMIBSwingState, OMIBStabilityState
import deeac.domain.ports.dtos.eeac_tree as node_dtos


class TestGeneratorTrajectoryCalculatorNode:

    def test_select_cluster(self, case1_generator_traj_calc_tree_node):
        assert case1_generator_traj_calc_tree_node.expected_inputs_dto_type == GeneratorTrajectoryCalculatorNodeInputs

    def test_inputs(self, case1_generator_traj_calc_tree_node, case1_zoomib, case1_network_line_fault):
        # Valid inputs
        inputs = GeneratorTrajectoryCalculatorNodeInputs(
            network=case1_network_line_fault,
            cluster_results=EEACClusterResults(
                critical_angle=0.5,
                critical_time=0.01,
                maximum_angle=4,
                maximum_time=3.4,
                critical_cluster=case1_zoomib.critical_cluster,
                non_critical_cluster=case1_zoomib.non_critical_cluster,
                dynamic_generators=case1_zoomib.critical_cluster.generators.union(
                    case1_zoomib.non_critical_cluster.generators
                ),
                omib_stability_state=OMIBStabilityState.POTENTIALLY_STABLE,
                omib_swing_state=OMIBSwingState.FORWARD
            )
        )
        case1_generator_traj_calc_tree_node.inputs = inputs
        assert case1_generator_traj_calc_tree_node.inputs == inputs

        # Invalid inputs
        with pytest.raises(EEACTreeNodeInputsException):
            case1_generator_traj_calc_tree_node.inputs = EACNodeInputs(omib=case1_zoomib)

    def test_verify_input_types(self, case1_generator_traj_calc_tree_node):
        assert case1_generator_traj_calc_tree_node.input_types == {
            EEACTreeNodeIOType.NETWORK,
            EEACTreeNodeIOType.CLUSTER_RESULTS,
            EEACTreeNodeIOType.OUTPUT_DIR
        }

    def test_verify_output_types(self, case1_generator_traj_calc_tree_node):
        assert case1_generator_traj_calc_tree_node.output_types == {
            EEACTreeNodeIOType.CRIT_CLUSTER,
            EEACTreeNodeIOType.NON_CRIT_CLUSTER,
            EEACTreeNodeIOType.DYNAMIC_GENERATORS
        }

    def test_can_be_leaf(self, case1_generator_traj_calc_tree_node):
        assert not case1_generator_traj_calc_tree_node.can_be_leaf()

    def test_run(self, case1_generator_traj_calc_tree_node):
        # Run and check outputs
        case1_generator_traj_calc_tree_node.run()

        outputs = case1_generator_traj_calc_tree_node.outputs
        assert type(outputs) == GeneratorTrajectoryCalculatorNodeOutputs
        assert {gen.name for gen in outputs.critical_cluster.generators} == {"GENA1"}
        assert {gen.name for gen in outputs.non_critical_cluster.generators} == {"GENB1", "GENB2", "NHVCEQ"}
        assert {gen.name for gen in outputs.dynamic_generators} == {"GENA1", "GENB1", "GENB2", "NHVCEQ"}
        gen = next(gen for gen in outputs.dynamic_generators)
        assert len(gen.observation_times) == 11

    def test_generate_report(self, case1_generator_traj_calc_tree_node):
        case1_generator_traj_calc_tree_node.run()
        report = re.sub(
            "\tExecution time: \\d+\\.\\d+ seconds\n",
            "",
            case1_generator_traj_calc_tree_node._generate_report()
        )
        assert report == (
            "Report for node 3_Generator Trajectory Calculator:\n"
            "\tConfiguration:\n"
            "\t\tNumber of during-fault intervals: 5\n"
            "\t\tNumber of post-fault intervals: 5\n"
            "\t\tCritical time shift: 10.0 ms\n"
            "\tInputs:\n"
            "\t\tCritical generators: GENA1\n"
            "\t\tCritical angle: 0.5 rad [28.648 deg]\n"
            "\t\tCritical time: 10.0 ms\n"
            "\t\tMaximum angle: 4.0 rad [229.183 deg]\n"
            "\t\tMaximum time: 3400.0 ms\n"
            "\t\tOMIB stability state: POTENTIALLY STABLE\n"
            "\t\tOMIB swing state: FORWARD\n"
            "\tOutput:\n"
            "\t\tUpdated generators: GENA1, GENB1, GENB2, NHVCEQ\n"
            "\t\tUpdate times (ms): 0, 2.0, 4.0, 6.0, 8.0, 10.0, 688.0, 1366.0, 2044.0, 2722.0, 3400.0\n"
        )

    def test_create_node(self):
        config = node_dtos.GeneratorTrajectoryCalculatorConfiguration(
            nb_during_fault_intervals=5,
            nb_post_fault_intervals=5,
            critical_time_shift=0.1
        )
        node_data = node_dtos.EEACTreeNode(
            name="test-node",
            id=1,
            type=node_dtos.EEACTreeNodeType.GENERATOR_TRAJECTORY_CALCULATOR,
            configuration=config
        )
        node = GeneratorTrajectoryCalculatorNode.create_node(node_data)
        assert type(node) == GeneratorTrajectoryCalculatorNode
        assert node._id == 1
        assert node._name == "test-node"
        assert node._nb_during_fault_intervals == 5
        assert node._nb_post_fault_intervals == 5
        assert node._critical_time_shift == 0.1
        assert not node.must_display_report
