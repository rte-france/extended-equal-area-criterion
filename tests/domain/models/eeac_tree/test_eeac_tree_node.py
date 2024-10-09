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

from deeac.domain.exceptions import (
    EEACTreeNodeInputsException, EEACTreeNodeOutputsException, EEACTreeNodeCancelledException,
    EEACNodeConfigurationException, NetworkStateException
)
from deeac.domain.models.eeac_tree import (
    CriticalClustersIdentifierNodeInputs, EEACTreeNodeIOType, EEACTreeNode, CriticalClustersIdentifierNode
)
import deeac.domain.ports.dtos.eeac_tree as node_dtos


class TestEEACTreeNode:

    def test_verify_inputs(
        self, case1_ccs_identifier_tree_node_no_inputs, case1_network, case1_line_fault_dynamic_generators
    ):
        with pytest.raises(EEACTreeNodeInputsException):
            case1_ccs_identifier_tree_node_no_inputs._verify_inputs()

        # Provide inputs
        case1_ccs_identifier_tree_node_no_inputs.inputs = CriticalClustersIdentifierNodeInputs(
            network=case1_network,
            dynamic_generators=case1_line_fault_dynamic_generators,
            output_dir=None
        )
        case1_ccs_identifier_tree_node_no_inputs._verify_inputs()

    def test_failed(self, case1_ccs_identifier_tree_node, case1_network, case1_line_fault_dynamic_generators):
        # Provide inputs
        case1_ccs_identifier_tree_node.inputs = CriticalClustersIdentifierNodeInputs(
            network=case1_network,
            dynamic_generators=case1_line_fault_dynamic_generators,
            output_dir=None
        )
        # No event provided
        case1_ccs_identifier_tree_node.run()
        assert case1_ccs_identifier_tree_node.failed

    def test_cancelled(self, case1_ccs_identifier_tree_node):
        assert not case1_ccs_identifier_tree_node.cancelled
        case1_ccs_identifier_tree_node.cancel()
        assert case1_ccs_identifier_tree_node.cancelled

    def test_input_types(self, case1_ccs_identifier_tree_node):
        assert case1_ccs_identifier_tree_node.input_types == {
            EEACTreeNodeIOType.NETWORK,
            EEACTreeNodeIOType.DYNAMIC_GENERATORS,
            EEACTreeNodeIOType.OUTPUT_DIR
        }

    def test_output_types(self, case1_ccs_identifier_tree_node):
        assert case1_ccs_identifier_tree_node.output_types == {
            EEACTreeNodeIOType.CLUSTERS_ITERATOR
        }

    def test_outputs(
        self, case1_ccs_identifier_tree_node, case1_network_line_fault, case1_line_fault_dynamic_generators
    ):
        with pytest.raises(EEACTreeNodeOutputsException):
            # Node not run
            case1_ccs_identifier_tree_node.outputs
        # Provide inputs
        case1_ccs_identifier_tree_node.inputs = CriticalClustersIdentifierNodeInputs(
            network=case1_network_line_fault,
            dynamic_generators=case1_line_fault_dynamic_generators,
            output_dir=None
        )
        # Run
        case1_ccs_identifier_tree_node.run()
        assert case1_ccs_identifier_tree_node.outputs is not None

    def test_inputs(
        self, case1_ccs_identifier_tree_node_no_inputs, case1_network_line_fault, case1_line_fault_dynamic_generators
    ):
        assert case1_ccs_identifier_tree_node_no_inputs.inputs is None
        # Provide inputs
        inputs = CriticalClustersIdentifierNodeInputs(
            network=case1_network_line_fault,
            dynamic_generators=case1_line_fault_dynamic_generators,
            output_dir=None
        )
        case1_ccs_identifier_tree_node_no_inputs.inputs = inputs
        assert case1_ccs_identifier_tree_node_no_inputs.inputs == inputs

    def test_id(self, case1_ccs_identifier_tree_node):
        assert case1_ccs_identifier_tree_node.id == 0

    def test_name(self, case1_ccs_identifier_tree_node):
        assert case1_ccs_identifier_tree_node.name == "ACC CCs Identifier"

    def test_complete_id(self, case1_ccs_identifier_tree_node):
        assert case1_ccs_identifier_tree_node.complete_id == "0_ACC CCs Identifier"
        case1_ccs_identifier_tree_node._name = None
        assert case1_ccs_identifier_tree_node.complete_id == 0

    def test_run(
        self, case1_ccs_identifier_tree_node_no_inputs, case1_network, case1_network_line_fault,
        case1_line_fault_dynamic_generators
    ):
        # No input provided
        case1_ccs_identifier_tree_node_no_inputs.run()
        assert case1_ccs_identifier_tree_node_no_inputs.failed
        assert type(case1_ccs_identifier_tree_node_no_inputs._exceptions.exceptions[0]) == EEACTreeNodeInputsException

        with pytest.raises(EEACTreeNodeOutputsException):
            # Check that no outputs were produced
            case1_ccs_identifier_tree_node_no_inputs.outputs

        # With inputs
        case1_ccs_identifier_tree_node_no_inputs.inputs = CriticalClustersIdentifierNodeInputs(
            network=case1_network,
            dynamic_generators=case1_line_fault_dynamic_generators,
            output_dir=None
        )
        # No event provided
        case1_ccs_identifier_tree_node_no_inputs.run()
        assert case1_ccs_identifier_tree_node_no_inputs.failed
        assert case1_ccs_identifier_tree_node_no_inputs._exceptions is not None
        assert type(case1_ccs_identifier_tree_node_no_inputs._exceptions.exceptions[0]) == NetworkStateException

        # Provide inputs
        case1_ccs_identifier_tree_node_no_inputs.inputs = CriticalClustersIdentifierNodeInputs(
            network=case1_network_line_fault,
            dynamic_generators=case1_line_fault_dynamic_generators,
            output_dir=None
        )
        # Run
        case1_ccs_identifier_tree_node_no_inputs.run()
        assert case1_ccs_identifier_tree_node_no_inputs.outputs is not None
        assert not case1_ccs_identifier_tree_node_no_inputs.failed
        assert case1_ccs_identifier_tree_node_no_inputs._exceptions is None

        # Cancelled
        case1_ccs_identifier_tree_node_no_inputs.cancel()
        case1_ccs_identifier_tree_node_no_inputs.run()
        assert case1_ccs_identifier_tree_node_no_inputs.cancelled
        assert type(
            case1_ccs_identifier_tree_node_no_inputs._exceptions.exceptions[0]
        ) == EEACTreeNodeCancelledException

    def test_generate_report(self, case1_ccs_identifier_tree_node):
        case1_ccs_identifier_tree_node.cancel()
        case1_ccs_identifier_tree_node.run()
        report = case1_ccs_identifier_tree_node._generate_report()
        report = re.sub("\tExecution time: \\d+\\.\\d+ seconds\n", "", report)
        assert report == (
            "Report for node 0_ACC CCs Identifier:\n"
            "\tExecution was cancelled.\n"
            "\tConfiguration:\n"
            "\t\tType of identifier: AccelerationCriticalClustersIdentifier\n"
            "\t\tThreshold: 0.5\n"
            "\t\tMinimum cluster power: 1000.0 kW\n"
            "\t\tThreshold decrement: 0.2\n"
            "\t\tMaximum number of candidates: 1\n"
            "\tInputs:\n"
            "\t\tGenerators: GENA1, GENB1, GENB2, NHVCEQ\n"
        )

        case1_ccs_identifier_tree_node._cancelled = False
        case1_ccs_identifier_tree_node._inputs = None
        case1_ccs_identifier_tree_node.run()
        report = case1_ccs_identifier_tree_node._generate_report()
        report = re.sub("\tExecution time: \\d+\\.\\d+ seconds\n", "", report)
        assert report == (
            "Report for node 0_ACC CCs Identifier:\n"
            "\tExecution failed due to the following errors: No inputs provided for node 0_ACC CCs Identifier. "
            "Expected inputs: dynamic_generators, network, output_dir.\n"
            "\tConfiguration:\n"
            "\t\tType of identifier: AccelerationCriticalClustersIdentifier\n"
            "\t\tThreshold: 0.5\n"
            "\t\tMinimum cluster power: 1000.0 kW\n"
            "\t\tThreshold decrement: 0.2\n"
            "\t\tMaximum number of candidates: 1\n"
        )

    def test_create_node(self, simple_ccs_identifier_node_data):
        node = EEACTreeNode.create_node(simple_ccs_identifier_node_data)
        assert type(node) == CriticalClustersIdentifierNode

    def test_validate_configuration(self, simple_ccs_identifier_node_data):
        with pytest.raises(EEACNodeConfigurationException):
            # Verify against selector
            EEACTreeNode.validate_configuration(
                simple_ccs_identifier_node_data,
                node_dtos.CriticalClusterSelectorConfiguration
            )
        # Verification OK
        EEACTreeNode.validate_configuration(
            simple_ccs_identifier_node_data,
            node_dtos.CriticalClustersIdentifierConfiguration
        )

    def test_reset(self, case1_ccs_identifier_tree_node):
        case1_ccs_identifier_tree_node.run()
        case1_ccs_identifier_tree_node.cancel()
        assert case1_ccs_identifier_tree_node.cancelled
        assert not case1_ccs_identifier_tree_node.failed
        assert case1_ccs_identifier_tree_node.inputs is not None
        assert case1_ccs_identifier_tree_node.outputs is not None
        assert case1_ccs_identifier_tree_node._execution_time > 0

        case1_ccs_identifier_tree_node.reset()
        assert not case1_ccs_identifier_tree_node.cancelled
        assert not case1_ccs_identifier_tree_node.failed
        assert case1_ccs_identifier_tree_node._inputs is None
        assert case1_ccs_identifier_tree_node._outputs is None
        assert case1_ccs_identifier_tree_node._execution_time == 0
