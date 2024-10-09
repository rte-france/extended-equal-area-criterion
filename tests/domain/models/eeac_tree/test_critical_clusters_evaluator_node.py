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
from pydantic import ValidationError

from deeac.domain.exceptions import EEACTreeNodeInputsException, EEACCriticalClusterEvaluatorSequenceException
from deeac.domain.models.eeac_tree import (
    CriticalClustersEvaluatorNodeInputs, EACNodeInputs, EEACTreeNodeIOType, CriticalClustersEvaluatorNodeOutputs,
    CriticalClustersEvaluatorNode, OMIBNode, EACNode, OMIBTrajectoryCalculatorNode
)
from deeac.domain.models.omib import OMIBStabilityState, OMIBSwingState
import deeac.domain.ports.dtos.eeac_tree as node_dtos


class TestCriticalClustersEvaluatorNode:

    def test_expected_inputs_dto_type(self, case1_ccs_evaluator_tree_node):
        assert case1_ccs_evaluator_tree_node.expected_inputs_dto_type == CriticalClustersEvaluatorNodeInputs

    def test_inputs(self, case1_ccs_evaluator_tree_node, case1_network, case1_zoomib):
        # Valid inputs
        inputs = CriticalClustersEvaluatorNodeInputs(
            network=case1_network,
            clusters_iterator=iter([(case1_zoomib.critical_cluster, case1_zoomib.non_critical_cluster)]),
            output_dir=None
        )
        case1_ccs_evaluator_tree_node.inputs = inputs
        assert case1_ccs_evaluator_tree_node.inputs == inputs

        # Invalid inputs
        with pytest.raises(EEACTreeNodeInputsException):
            case1_ccs_evaluator_tree_node.inputs = EACNodeInputs(omib=case1_zoomib)

    def test_verify_input_types(self, case1_ccs_evaluator_tree_node):
        assert case1_ccs_evaluator_tree_node.input_types == {
            EEACTreeNodeIOType.NETWORK,
            EEACTreeNodeIOType.CLUSTERS_ITERATOR,
            EEACTreeNodeIOType.OUTPUT_DIR
        }

    def test_verify_output_types(self, case1_ccs_evaluator_tree_node):
        assert case1_ccs_evaluator_tree_node.output_types == {EEACTreeNodeIOType.CLUSTER_RESULTS_ITERATOR}

    def test_can_be_leaf(self, case1_ccs_evaluator_tree_node):
        assert not case1_ccs_evaluator_tree_node.can_be_leaf()

    def test_run(self, case1_ccs_evaluator_tree_node, case1_line_fault_zoomib_eac):
        # Run and check outputs
        case1_ccs_evaluator_tree_node.run()

        outputs = case1_ccs_evaluator_tree_node.outputs
        assert type(outputs) == CriticalClustersEvaluatorNodeOutputs
        # Results for only 1 cluster, ZOOMIB
        iterator = outputs.cluster_results_iterator
        results = next(iterator)
        assert cmath.isclose(results.critical_angle, case1_line_fault_zoomib_eac.critical_clearing_angle, abs_tol=10e-9)
        assert cmath.isclose(results.maximum_angle, case1_line_fault_zoomib_eac.maximum_angle, abs_tol=10e-9)
        assert cmath.isclose(results.critical_time, 0.26732036492951583, abs_tol=10e-9)
        assert cmath.isclose(results.maximum_time, 0.5087925117043797, abs_tol=10e-9)
        assert len(results.critical_cluster.generators) == 1
        assert len(results.non_critical_cluster.generators) == 3
        assert len(results.dynamic_generators) == 4
        assert list(results.critical_cluster.generators)[0].name == "GENA1"
        assert results.omib_stability_state == OMIBStabilityState.POTENTIALLY_STABLE
        assert results.omib_swing_state == OMIBSwingState.FORWARD
        with pytest.raises(StopIteration):
            next(iterator)

    def test_generate_report(self, case1_ccs_evaluator_tree_node, case1_line_fault_zoomib_eac):
        case1_ccs_evaluator_tree_node.run()
        report = re.sub("\tExecution time: \\d+\\.\\d+ seconds\n", "", case1_ccs_evaluator_tree_node._generate_report())
        assert report == (
            "Report for node 1_Basic CC Evaluator:\n"
            "\tOutputs:\n"
            "\t\tCluster 0:\n"
            "\t\t\tCritical generators: GENA1\n"
            "\t\t\tCritical angle: 1.201 rad [68.826 deg]\n"
            "\t\t\tCritical time: 267.32 ms\n"
            "\t\t\tMaximum angle: 2.238 rad [68.826 deg]\n"
            "\t\t\tMaximum time: 508.793 ms\n"
            "\t\t\tOMIB stability state: POTENTIALLY STABLE\n"
            "\t\t\tOMIB swing state: FORWARD\n"
        )

    def test_create_node(self):
        # At least one node must be specified
        with pytest.raises(ValidationError):
            node_dtos.CriticalClustersEvaluatorConfiguration(
                evaluation_sequence=node_dtos.EEACClusterEvaluationSequence(
                    nodes=[]
                )
            )
        with pytest.raises(EEACCriticalClusterEvaluatorSequenceException):
            # Bad evaluation sequence as last node must output EEAC cluster results
            config = node_dtos.CriticalClustersEvaluatorConfiguration(
                evaluation_sequence=node_dtos.EEACClusterEvaluationSequence(
                    nodes=[
                        node_dtos.EEACClusterEvaluationSequenceNode(
                            id=11,
                            name="ZOOMIB",
                            type=node_dtos.EEACTreeNodeType.OMIB,
                            configuration=node_dtos.OMIBConfiguration(
                                omib_type=node_dtos.OMIBType.ZOOMIB
                            )
                        )
                    ]
                )
            )
            node_data = node_dtos.EEACTreeNode(
                name="test-node",
                id=1,
                type=node_dtos.EEACTreeNodeType.CRITICAL_CLUSTERS_EVALUATOR,
                configuration=config
            )
            node = CriticalClustersEvaluatorNode.create_node(node_data)

        # Valid sequence
        config = node_dtos.CriticalClustersEvaluatorConfiguration(
            evaluation_sequence=node_dtos.EEACClusterEvaluationSequence(
                nodes=[
                    node_dtos.EEACClusterEvaluationSequenceNode(
                        id=11,
                        name="ZOOMIB",
                        type=node_dtos.EEACTreeNodeType.OMIB,
                        configuration=node_dtos.OMIBConfiguration(
                            omib_type=node_dtos.OMIBType.ZOOMIB
                        )
                    ),
                    node_dtos.EEACClusterEvaluationSequenceNode(
                        id=12,
                        name="EAC",
                        type=node_dtos.EEACTreeNodeType.EAC,
                        configuration=node_dtos.EACConfiguration(
                            angle_increment=0.1,
                            max_integration_angle=360
                        )
                    ),
                    node_dtos.EEACClusterEvaluationSequenceNode(
                        id=13,
                        name="OMIB Trajectory Calculator",
                        type=node_dtos.EEACTreeNodeType.OMIB_TRAJECTORY_CALCULATOR,
                        configuration=node_dtos.OMIBTrajectoryCalculatorConfiguration(
                            calculator_type=node_dtos.OMIBTrajectoryCalculatorType.TAYLOR
                        )
                    )
                ]
            )
        )
        # Create node
        node_data = node_dtos.EEACTreeNode(
            name="test-node",
            id=1,
            type=node_dtos.EEACTreeNodeType.CRITICAL_CLUSTERS_EVALUATOR,
            configuration=config
        )
        node = CriticalClustersEvaluatorNode.create_node(node_data)
        assert type(node) == CriticalClustersEvaluatorNode
        assert node._id == 1
        assert node._name == "test-node"
        assert node._evaluation_tree._name == "Cluster evaluation tree"
        assert len(node._evaluation_tree._tree_graph.nodes) == 3
        assert type(node._evaluation_tree[11]) == OMIBNode
        assert type(node._evaluation_tree[12]) == EACNode
        assert type(node._evaluation_tree[13]) == OMIBTrajectoryCalculatorNode
