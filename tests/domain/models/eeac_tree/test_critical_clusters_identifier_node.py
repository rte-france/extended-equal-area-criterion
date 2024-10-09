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
from deeac.domain.models.eeac_tree import (
    CriticalClustersIdentifierNodeInputs, EACNodeInputs, EEACTreeNodeIOType, CriticalClustersIdentifierNodeOutputs,
    CriticalClustersIdentifierNode
)
from deeac.domain.services.critical_clusters_identifier import AccelerationCriticalClustersIdentifier
from deeac.domain.models import Value, Unit
import deeac.domain.ports.dtos.eeac_tree as node_dtos


class TestCriticalClustersIdentifierNode:

    def test_expected_inputs_dto_type(self, case1_ccs_identifier_tree_node):
        assert case1_ccs_identifier_tree_node.expected_inputs_dto_type == CriticalClustersIdentifierNodeInputs

    def test_inputs(
        self, case1_ccs_identifier_tree_node, case1_network, case1_line_fault_dynamic_generators, case1_zoomib
    ):
        # Valid inputs
        inputs = CriticalClustersIdentifierNodeInputs(
            network=case1_network,
            dynamic_generators=case1_line_fault_dynamic_generators
        )
        case1_ccs_identifier_tree_node.inputs = inputs
        assert case1_ccs_identifier_tree_node.inputs == inputs

        # Invalid inputs
        with pytest.raises(EEACTreeNodeInputsException):
            case1_ccs_identifier_tree_node.inputs = EACNodeInputs(omib=case1_zoomib)

    def test_verify_input_types(self, case1_ccs_identifier_tree_node):
        assert case1_ccs_identifier_tree_node.input_types == {
            EEACTreeNodeIOType.NETWORK,
            EEACTreeNodeIOType.DYNAMIC_GENERATORS,
            EEACTreeNodeIOType.OUTPUT_DIR
        }

    def test_verify_output_types(self, case1_ccs_identifier_tree_node):
        assert case1_ccs_identifier_tree_node.output_types == {EEACTreeNodeIOType.CLUSTERS_ITERATOR}

    def test_can_be_leaf(self, case1_ccs_identifier_tree_node):
        assert not case1_ccs_identifier_tree_node.can_be_leaf()

    def test_run(self, case1_ccs_identifier_tree_node, case1_network_line_fault, case1_line_fault_dynamic_generators):
        # Run and check outputs
        case1_ccs_identifier_tree_node.run()

        outputs = case1_ccs_identifier_tree_node.outputs
        assert type(outputs) == CriticalClustersIdentifierNodeOutputs
        iterator = outputs.clusters_iterator
        critical_cluster, _ = next(iterator)
        assert len(critical_cluster.generators) == 1
        assert list(critical_cluster.generators)[0].name == "GENA1"
        with pytest.raises(StopIteration):
            next(iterator)

        # Tries with another configuration
        config = node_dtos.CriticalClustersIdentifierConfiguration(
            identifier_type=node_dtos.CriticalClustersIdentifierType.ACCELERATION,
            threshold=0.5,
            min_cluster_power="1000MW",
            threshold_decrement=0.2
        )
        node_data = node_dtos.EEACTreeNode(
            name="test-node",
            id=1,
            type=node_dtos.EEACTreeNodeType.CRITICAL_CLUSTERS_IDENTIFIER,
            configuration=config
        )
        node = CriticalClustersIdentifierNode.create_node(node_data)
        node.inputs = CriticalClustersIdentifierNodeInputs(
            network=case1_network_line_fault,
            dynamic_generators=case1_line_fault_dynamic_generators
        )
        node.run()
        outputs = node.outputs
        assert type(outputs) == CriticalClustersIdentifierNodeOutputs
        iterator = outputs.clusters_iterator
        critical_cluster, _ = next(iterator)
        assert len(critical_cluster.generators) == 3
        assert {gen.name for gen in critical_cluster.generators} == {"GENA1", "GENB1", "GENB2"}
        critical_cluster, _ = next(iterator)
        assert len(critical_cluster.generators) == 2
        assert {gen.name for gen in critical_cluster.generators} == {"GENA1", "GENB1"}
        with pytest.raises(StopIteration):
            next(iterator)


    def test_generate_report(self, case1_ccs_identifier_tree_node):
        case1_ccs_identifier_tree_node.run()
        report = re.sub(
            "\tExecution time: \\d+\\.\\d+ seconds\n",
            "",
            case1_ccs_identifier_tree_node._generate_report()
        )
        assert report == (
            "Report for node 0_ACC CCs Identifier:\n"
            "\tConfiguration:\n"
            "\t\tType of identifier: AccelerationCriticalClustersIdentifier\n"
            "\t\tThreshold: 0.5\n"
            "\t\tMinimum cluster power: 1000.0 kW [Base: 100.0 MW]\n"
            "\t\tThreshold decrement: 0.2\n"
            "\t\tMaximum number of candidates: 1\n"
            "\tInputs:\n"
            "\t\tGenerators: GENA1, GENB1, GENB2, NHVCEQ\n"
            "\tOutputs:\n\t\tCritical cluster candidates:\n"
        )

    def test_create_node(self):
        config = node_dtos.CriticalClustersIdentifierConfiguration(
            identifier_type=node_dtos.CriticalClustersIdentifierType.ACCELERATION,
            threshold=0.7,
            max_number_candidates=1,
            min_cluster_power="100kW",
            threshold_decrement=0.3
        )
        node_data = node_dtos.EEACTreeNode(
            name="test-node",
            id=1,
            type=node_dtos.EEACTreeNodeType.CRITICAL_CLUSTERS_IDENTIFIER,
            configuration=config
        )
        node = CriticalClustersIdentifierNode.create_node(node_data)
        assert type(node) == CriticalClustersIdentifierNode
        assert node._id == 1
        assert node._name == "test-node"
        assert node._identifier_type == AccelerationCriticalClustersIdentifier
        assert node._threshold == 0.7
        assert node._max_number_candidates == 1
        assert node._critical_generator_names is None
        assert node._observation_moment_id == -1
        assert node._min_cluster_power == Value(100, Unit.KW)
        assert node._threshold_decrement == 0.3
