# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest

from deeac.domain.models.eeac_tree import (
    CriticalClustersIdentifierNode, CriticalClusterSelectorNode, CriticalClustersEvaluatorNode, OMIBNode, EACNode,
    GeneratorTrajectoryCalculatorNode, OMIBTrajectoryCalculatorNode, EEACTree
)
from deeac.domain.models.omib import ZOOMIB, DOMIB
from deeac.domain.services.critical_clusters_identifier import AccelerationCriticalClustersIdentifier
from deeac.domain.models.rotor_angle_trajectory_calculator.taylor_series import OMIBTaylorSeries
from deeac.domain.services.critical_cluster_selector import MinCriticalClusterSelector
from deeac.domain.exceptions import (
    EEACTreeNodeException, EEACTreeChildException, DEEACExceptionList, EEACTreeLeafException,
    EEACTreeDuplicateIDException
)
from deeac.domain.ports.dtos.eeac_tree import (
    EACConfiguration, EEACTreeNode, EEACTreeNodeType, EEACClusterEvaluationSequenceNode,
    OMIBTrajectoryCalculatorConfiguration, OMIBTrajectoryCalculatorType
)


class TestEEACTree:

    def test_name(self, basic_domib_eeac_tree):
        assert basic_domib_eeac_tree.name == "Basic DOMIB tree"

    def test_predecessor(self, basic_domib_eeac_tree):
        assert basic_domib_eeac_tree.predecessor(basic_domib_eeac_tree.root) is None
        assert basic_domib_eeac_tree.predecessor(basic_domib_eeac_tree[1]) == basic_domib_eeac_tree.root

        node = EACNode(3, "test", 4, 5)
        with pytest.raises(EEACTreeNodeException):
            basic_domib_eeac_tree.predecessor(node)

    def test_getitem(self, basic_domib_eeac_tree, case1_ccs_identifier_tree_node):
        assert basic_domib_eeac_tree[0] == case1_ccs_identifier_tree_node
        with pytest.raises(EEACTreeNodeException):
            basic_domib_eeac_tree[10]

    def test_root(self, basic_domib_eeac_tree, case1_ccs_identifier_tree_node):
        assert basic_domib_eeac_tree.root == case1_ccs_identifier_tree_node

    def test_deep_first_traversal(self, basic_domib_eeac_tree):
        nodes = basic_domib_eeac_tree.deep_first_traversal()
        for i, node in enumerate(nodes):
            assert node.id == i

    def test_add_node(self, basic_domib_eeac_tree):
        tree = basic_domib_eeac_tree._tree_graph

        node_data = EEACTreeNode(
            name="test0",
            id=18,
            type=EEACTreeNodeType.EAC,
            configuration=EACConfiguration(
                angle_increment=3.0
            )
        )
        # Node with no children that cannot be leaf
        with pytest.raises(DEEACExceptionList) as exception:
            EEACTree.add_node(tree, node_data, basic_domib_eeac_tree[4])
        exception_list = exception.value
        assert len(exception_list.exceptions) == 1
        assert type(exception_list.exceptions[0]) == EEACTreeLeafException

        # Duplicate ID.
        with pytest.raises(DEEACExceptionList) as e:
            EEACTree.add_node(tree, node_data, basic_domib_eeac_tree[4], True)
        assert len(e.value.exceptions) == 1
        assert type(e.value.exceptions[0]) == EEACTreeDuplicateIDException
        assert e.value.exceptions[0].node_id == 18

        # Node can be added if evaluation tree
        node_data.id = 181
        node = EEACTree.add_node(tree, node_data, basic_domib_eeac_tree[4], True)
        assert type(node) == EACNode
        assert node.id == 181
        assert node.name == "test0"
        assert node._angle_increment == 3.0
        assert node._max_integration_angle == 360

        # Add valid node
        node_data = EEACTreeNode(
            name="test",
            id=19,
            type=EEACTreeNodeType.EAC,
            configuration=EACConfiguration(
                angle_increment=3.1
            ),
            children=[
                EEACClusterEvaluationSequenceNode(
                    id=13,
                    name="test2",
                    type=EEACTreeNodeType.OMIB_TRAJECTORY_CALCULATOR,
                    configuration=OMIBTrajectoryCalculatorConfiguration(
                        calculator_type=OMIBTrajectoryCalculatorType.TAYLOR
                    )
                )
            ]
        )
        node = EEACTree.add_node(tree, node_data, basic_domib_eeac_tree[4])
        assert type(node) == EACNode
        assert node.id == 19
        assert node.name == "test"
        assert node._angle_increment == 3.1
        assert node._max_integration_angle == 360

        # Check that child was also added
        node = basic_domib_eeac_tree[13]
        assert type(node) == OMIBTrajectoryCalculatorNode
        assert node.id == 13
        assert node.name == "test2"
        assert node._calculator_type == OMIBTaylorSeries

        # Add incompatible node
        node_data.id = 191
        with pytest.raises(DEEACExceptionList) as exception:
            EEACTree.add_node(tree, node_data, basic_domib_eeac_tree[3])
        exception_list = exception.value
        assert len(exception_list.exceptions) == 1
        assert type(exception_list.exceptions[0]) == EEACTreeChildException

    def test_create_tree(self, basic_domib_eeac_tree):
        assert basic_domib_eeac_tree.name == "Basic DOMIB tree"

        # First node
        node0 = basic_domib_eeac_tree[0]
        assert node0 == basic_domib_eeac_tree.root
        assert basic_domib_eeac_tree.predecessor(node0) is None
        assert type(node0) == CriticalClustersIdentifierNode
        assert node0.id == 0
        assert node0.name == "ACC CCs Identifier"
        assert node0._identifier_type == AccelerationCriticalClustersIdentifier
        assert node0._threshold == 0.5
        assert node0._max_number_candidates == 1

        # Second node
        node1 = basic_domib_eeac_tree[1]
        assert basic_domib_eeac_tree.predecessor(node1) == node0
        assert type(node1) == CriticalClustersEvaluatorNode
        assert node1.id == 1
        assert node1.name == "Basic CC Evaluator"
        assert type(node1._evaluation_tree) == EEACTree
        evaluation_tree = node1._evaluation_tree
        # Node 1.1
        node11 = evaluation_tree[11]
        assert evaluation_tree.predecessor(node11) is None
        assert evaluation_tree.root == node11
        assert type(node11) == OMIBNode
        assert node11.id == 11
        assert node11.name == "Basic CC Evaluator - ZOOMIB"
        assert node11._omib_type == ZOOMIB
        # Node 1.2
        node12 = evaluation_tree[12]
        assert evaluation_tree.predecessor(node12) == node11
        assert type(node12) == EACNode
        assert node12.id == 12
        assert node12.name == "Basic CC Evaluator - EAC"
        assert node12._angle_increment == 1.8
        assert node12._max_integration_angle == 360
        # Node 1.3
        node13 = evaluation_tree[13]
        assert evaluation_tree.predecessor(node13) == node12
        assert type(node13) == OMIBTrajectoryCalculatorNode
        assert node13.id == 13
        assert node13.name == "Basic CC Evaluator - OMIB Trajectory Calculator"
        assert node13._calculator_type == OMIBTaylorSeries

        # Third node
        node2 = basic_domib_eeac_tree[2]
        assert basic_domib_eeac_tree.predecessor(node2) == node1
        assert type(node2) == CriticalClusterSelectorNode
        assert node2.id == 2
        assert node2.name == "MIN CC Selector"
        assert node2._selector_type == MinCriticalClusterSelector

        # Fourth node
        node3 = basic_domib_eeac_tree[3]
        assert basic_domib_eeac_tree.predecessor(node3) == node2
        assert type(node3) == GeneratorTrajectoryCalculatorNode
        assert node3.id == 3
        assert node3.name == "Generator Trajectory Calculator"
        assert node3._nb_during_fault_intervals == 5
        assert node3._nb_post_fault_intervals == 5

        # Fifth node
        node4 = basic_domib_eeac_tree[4]
        assert basic_domib_eeac_tree.predecessor(node4) == node3
        assert type(node4) == OMIBNode
        assert node4.id == 4
        assert node4.name == "DOMIB"
        assert node4._omib_type == DOMIB

        # Sixth node
        node5 = basic_domib_eeac_tree[5]
        assert basic_domib_eeac_tree.predecessor(node5) == node4
        assert type(node5) == EACNode
        assert node5.id == 5
        assert node5.name == "DOMIB EAC"
        assert node5._angle_increment == 1.8
        assert node5._max_integration_angle == 360

        # Last node
        node6 = basic_domib_eeac_tree[6]
        assert basic_domib_eeac_tree.predecessor(node6) == node5
        assert type(node6) == OMIBTrajectoryCalculatorNode
        assert node6.id == 6
        assert node6.name == "DOMIB Trajectory Calculator"
        assert node6._calculator_type == OMIBTaylorSeries
