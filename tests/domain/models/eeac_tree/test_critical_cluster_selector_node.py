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
    CriticalClusterSelectorNodeInputs, EACNodeInputs, EEACTreeNodeIOType, CriticalClusterSelectorNodeOutputs,
    CriticalClusterSelectorNode, EEACClusterResults
)
from deeac.domain.services.critical_cluster_selector import MinCriticalClusterSelector
from deeac.domain.models.omib import OMIBStabilityState, OMIBSwingState
import deeac.domain.ports.dtos.eeac_tree as node_dtos


class TestCriticalClusterSelectorNode:

    def test_select_cluster(self, case1_cc_selector_tree_node):
        assert case1_cc_selector_tree_node.expected_inputs_dto_type == CriticalClusterSelectorNodeInputs

    def test_inputs(self, case1_cc_selector_tree_node, case1_zoomib):
        inputs = [
            EEACClusterResults(
                critical_angle=1,
                critical_time=0.1,
                maximum_angle=2,
                maximum_time=1.4,
                critical_cluster=case1_zoomib.critical_cluster,
                non_critical_cluster=case1_zoomib.non_critical_cluster,
                dynamic_generators=case1_zoomib.critical_cluster.generators.union(
                    case1_zoomib.non_critical_cluster.generators
                ),
                omib_stability_state=OMIBStabilityState.POTENTIALLY_STABLE,
                omib_swing_state=OMIBSwingState.FORWARD
            )
        ]

        # Valid inputs
        inputs = CriticalClusterSelectorNodeInputs(cluster_results_iterator=iter(inputs))
        case1_cc_selector_tree_node.inputs = inputs
        assert case1_cc_selector_tree_node.inputs == inputs

        # Invalid inputs
        with pytest.raises(EEACTreeNodeInputsException):
            case1_cc_selector_tree_node.inputs = EACNodeInputs(omib=case1_zoomib)

    def test_verify_input_types(self, case1_cc_selector_tree_node):
        assert case1_cc_selector_tree_node.input_types == {
            EEACTreeNodeIOType.CLUSTER_RESULTS_ITERATOR,
            EEACTreeNodeIOType.OUTPUT_DIR
        }

    def test_verify_output_types(self, case1_cc_selector_tree_node):
        assert case1_cc_selector_tree_node.output_types == {EEACTreeNodeIOType.CLUSTER_RESULTS}

    def test_can_be_leaf(self, case1_cc_selector_tree_node):
        assert case1_cc_selector_tree_node.can_be_leaf()

    def test_run(self, case1_cc_selector_tree_node):
        # TODO: update results of critical cluster identification
        # Run and check outputs
        case1_cc_selector_tree_node.run()

        outputs = case1_cc_selector_tree_node.outputs
        assert type(outputs) == CriticalClusterSelectorNodeOutputs
        results = outputs.cluster_results
        # Skip first results as they are not selected
        next(case1_cc_selector_tree_node.inputs.cluster_results_iterator)
        #assert results == next(case1_cc_selector_tree_node.inputs.cluster_results_iterator)

    def test_generate_report(self, case1_cc_selector_tree_node):
        case1_cc_selector_tree_node.run()
        report = re.sub("\tExecution time: \\d+\\.\\d+ seconds\n", "", case1_cc_selector_tree_node._generate_report())
        assert report == (
            "Report for node 2_MIN CC Selector:\n"
            "\tConfiguration:\n"
            "\t\tType of selector: MinCriticalClusterSelector\n"
            "\tInputs:\n"
            "\t\tCluster 0:\n"
            "\t\t\tCritical generators: GENA1\n"
            "\t\t\tCritical angle: 1.0 rad [57.296 deg]\n"
            "\t\t\tCritical time: 100.0 ms\n"
            "\t\t\tMaximum angle: 2.0 rad [114.592 deg]\n"
            "\t\t\tMaximum time: 1400.0 ms\n"
            "\t\t\tOMIB stability state: POTENTIALLY STABLE\n"
            "\t\t\tOMIB swing state: FORWARD\n"
            "\t\tCluster 1:\n"
            "\t\t\tCritical generators: GENA1\n"
            "\t\t\tCritical angle: 0.5 rad [28.648 deg]\n"
            "\t\t\tCritical time: 10.0 ms\n"
            "\t\t\tMaximum angle: 4.0 rad [229.183 deg]\n"
            "\t\t\tMaximum time: 3400.0 ms\n"
            "\t\t\tOMIB stability state: POTENTIALLY STABLE\n"
            "\t\t\tOMIB swing state: FORWARD\n"
            "\tOutputs:\n"
            "\t\tCritical generators: GENA1\n"
            "\t\tCritical angle: 0.5 rad [28.648 deg]\n"
            "\t\tCritical time: 10.0 ms\n"
            "\t\tMaximum angle: 4.0 rad [229.183 deg]\n"
            "\t\tMaximum time: 3400.0 ms\n"
            "\t\tOMIB stability state: POTENTIALLY STABLE\n"
            "\t\tOMIB swing state: FORWARD"
        )

    def test_create_node(self):
        config = node_dtos.CriticalClusterSelectorConfiguration(
            selector_type=node_dtos.CriticalClusterSelectorType.MIN,
            display_report=True
        )
        node_data = node_dtos.EEACTreeNode(
            name="test-node",
            id=1,
            type=node_dtos.EEACTreeNodeType.CRITICAL_CLUSTER_SELECTOR,
            configuration=config
        )
        node = CriticalClusterSelectorNode.create_node(node_data)
        assert type(node) == CriticalClusterSelectorNode
        assert node._id == 1
        assert node._name == "test-node"
        assert node._selector_type == MinCriticalClusterSelector
        assert node.must_display_report
