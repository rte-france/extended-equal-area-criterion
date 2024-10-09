# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import numpy as np
from itertools import tee
from typing import Union, Iterator, Tuple, Type, Optional, TYPE_CHECKING

from deeac.domain.exceptions import (
    EEACCriticalClusterEvaluatorSequenceException, EEACTreeNodeInputsException, EEACCriticalClusterNoResultsException
)
from .eeac_tree_node import EEACTreeNode, EEACTreeNodeIOs, EEACClusterResults, EEACTreeNodeIOType
from deeac.domain.models import Network, GeneratorCluster
from deeac.domain.models.omib import OMIBStabilityState
import deeac.domain.ports.dtos.eeac_tree as node_dtos


if TYPE_CHECKING:
    from deeac.domain.models.eeac_tree import EEACTree


class CriticalClustersEvaluatorNodeInputs(EEACTreeNodeIOs):
    """
    Inputs of this node.
    """
    network: Network
    clusters_iterator: Iterator[Tuple[GeneratorCluster, GeneratorCluster]]
    output_dir: Optional[str]


class CriticalClustersEvaluatorNodeOutputs(EEACTreeNodeIOs):
    """
    Outputs of this node.
    """
    cluster_results_iterator: Iterator[EEACClusterResults]


class CriticalClustersEvaluatorNode(EEACTreeNode):
    """
    Node of and EEAC execution tree representing a critical cluster evaluator.
    """

    def __init__(self, id: Union[str, int], name: str, evaluation_tree: 'EEACTree', must_display_report: bool = False):
        """
        Initialize the tree node

        :param id: Unique identifier of the node.
        :param name: Name of the node.
        :param evaluation_tree: Evaluation tree used to get results for a cluster candidate. This tree must be valid
                                and compatible with the inputs and outputs of this node.
        :param must_display_report: True if a report must be outputted for the node
        """
        super().__init__(id, name, must_display_report)
        self._evaluation_tree = evaluation_tree
        self._cluster_results = None

        # Keep track of failed clusters
        self._failed_clusters = set()

        # Prepare the inputs and outputs
        self._input_types = {
            EEACTreeNodeIOType.NETWORK,
            EEACTreeNodeIOType.CLUSTERS_ITERATOR,
            EEACTreeNodeIOType.OUTPUT_DIR
        }
        self._output_types = {EEACTreeNodeIOType.CLUSTER_RESULTS_ITERATOR}

        # The central result, CCT or stability
        self.critical_result = None

    @property
    def expected_inputs_dto_type(self) -> Type[EEACTreeNodeIOs]:
        """
        Return the expected type of DTO for the inputs.

        :return: The type of DTO.
        """
        return CriticalClustersEvaluatorNodeInputs

    @EEACTreeNode.inputs.setter
    def inputs(self, inputs: EEACTreeNodeIOs):
        """
        Provide the inputs to this node.

        :param inputs: Input values.
        :raise EEACTreeNodeInputsException if the input is not expected by this node.
        """
        try:
            assert type(inputs) == CriticalClustersEvaluatorNodeInputs
            self._inputs = inputs
        except AssertionError:
            raise EEACTreeNodeInputsException(self)

    def can_be_leaf(self) -> bool:
        """
        Determine if the node can be a leaf in the tree.

        :return: True if the node can be a leaf, False otherwise.
        """
        return False

    def _run(self):
        """
        Run the node in order to produce the output values.

        :raise: A DEEACException in case of errors.
        """
        # Verify inputs
        self._verify_inputs()
        self._failed_clusters = set()

        # Create EEAC service in charge of evaluating the clusters
        from deeac.domain.services.eeac import EEAC
        self._eeac = EEAC(self._evaluation_tree, self._inputs.network)

        # Get node sequence (only one branch)
        nodes = self._evaluation_tree.deep_first_traversal()

        # Iterate through the clusters
        cluster_results = []
        self._inputs.clusters_iterator, clusters_iterator = tee(self._inputs.clusters_iterator)
        for cluster_nb, (critical_cluster, non_critical_cluster) in enumerate(clusters_iterator):
            # Create output directory path
            if self._inputs.output_dir is None:
                output_dir = None
            else:
                output_dir = f"{self._inputs.output_dir}/{self.complete_id}/cluster{cluster_nb}"
            # Provide inputs and run evaluation
            self._eeac.provide_inputs(
                {
                    EEACTreeNodeIOType.CRIT_CLUSTER: critical_cluster,
                    EEACTreeNodeIOType.NON_CRIT_CLUSTER: non_critical_cluster,
                    EEACTreeNodeIOType.OUTPUT_DIR: output_dir
                }
            )
            self._eeac.run()
            if self._eeac.critical_result is not None:
                self.critical_result = self._eeac.critical_result

            # Get results from last node in the evaluation sequence
            if nodes[-1].failed or nodes[-1].cancelled:
                # Node failed
                self._failed_clusters.add(cluster_nb)
            else:
                # Add results (should not produce any error as output types of last node are valid)
                results = nodes[-1].outputs.cluster_results
                cluster_results.append(results)

            # Reset tree nodes for next run
            self._eeac.reset()

        if len(cluster_results) == 0:
            # Failed if not results were produced
            self.failed
            raise EEACCriticalClusterNoResultsException(self)

        # Keep a copy of the iterator
        cluster_results, self._cluster_results = tee(iter(cluster_results))
        self._outputs = CriticalClustersEvaluatorNodeOutputs(
            cluster_results_iterator=cluster_results
        )

    def _generate_report(self) -> str:
        """
        Generate an output report as a string.
        """
        # Get initial report
        report = f"{super()._generate_report()}"

        # Outputs
        if not self.cancelled and not self.failed:
            report = f"{report}\tOutputs:\n"
            self._cluster_results, cluster_results = tee(iter(self._cluster_results))
            self._inputs.clusters_iterator, clusters_iterator = tee(self._inputs.clusters_iterator)
            for cluster_nb, _ in enumerate(clusters_iterator):
                if cluster_nb in self._failed_clusters:
                    # Cluster failed
                    continue
                results = next(cluster_results)
                critical_generators = ", ".join(sorted(gen.name for gen in results.critical_cluster.generators))
                if results.omib_stability_state == OMIBStabilityState.POTENTIALLY_STABLE:
                    report = (
                        f"{report}\t\tCluster {cluster_nb}:\n"
                        f"\t\t\tCritical generators: {critical_generators}\n"
                        f"\t\t\tCritical angle: {round(results.critical_angle, 3)} rad "
                        f"[{round(np.rad2deg(results.critical_angle), 3)} deg]\n"
                        f"\t\t\tCritical time: {round(results.critical_time * 1000, 3)} ms\n"
                        f"\t\t\tMaximum angle: {round(results.maximum_angle, 3)} rad "
                        f"[{round(np.rad2deg(results.critical_angle), 3)} deg]\n"
                        f"\t\t\tMaximum time: {round(results.maximum_time * 1000, 3)} ms\n"
                        f"\t\t\tOMIB stability state: {results.omib_stability_state.value}\n"
                        f"\t\t\tOMIB swing state: {results.omib_swing_state.value}\n"
                    )
                else:
                    report = (
                        f"{report}\t\tCluster {cluster_nb}:\n"
                        f"\t\t\tCritical generators: {critical_generators}\n"
                        f"\t\t\tOMIB stability state: {results.omib_stability_state.value}\n"
                        f"\t\t\tOMIB swing state: {results.omib_swing_state.value}\n"
                    )

        if len(self._failed_clusters) > 0:
            # Some cluster evaluations failed
            self._inputs.clusters_iterator, clusters_iterator = tee(self._inputs.clusters_iterator)
            input_clusters = list(clusters_iterator)
            report = f"{report}\tFailed cluster evaluations:\n"
            for cluster_nb in self._failed_clusters:
                critical_generators = ", ".join(sorted(gen.name for gen in input_clusters[cluster_nb][0].generators))
                report = (
                    f"{report}\t\tCluster {cluster_nb}:\n"
                    f"\t\t\tCritical generators: {critical_generators}\n"
                )
        return report

    @classmethod
    def create_node(cls, node_data: node_dtos.EEACTreeNode) -> 'EEACTreeNode':
        """
        Create an EEAC tree node based on DTO values.

        :param node_data: Node data to use for creation.
        :return: The EEAC tree node.
        :raise EEACTreeNodeTypeException: If the type of node is not recognized.
        :raise EEACNodeConfigurationException if the node configuration is not valid.
        """
        # Validate configuration
        EEACTreeNode.validate_configuration(node_data, node_dtos.CriticalClustersEvaluatorConfiguration)

        # Create evaluation tree
        from deeac.domain.models.eeac_tree import EEACTree
        configuration = node_data.configuration
        evaluation_tree = EEACTree.create_tree(configuration.evaluation_sequence)

        # Verify that first node inputs and last node outputs are valid
        first_node = evaluation_tree.root
        last_node = evaluation_tree[node_data.configuration.evaluation_sequence.nodes[-1].id]
        try:
            assert EEACTreeNodeIOType.CRIT_CLUSTER in first_node.input_types
            assert EEACTreeNodeIOType.NON_CRIT_CLUSTER in first_node.input_types
            assert EEACTreeNodeIOType.CLUSTER_RESULTS in last_node.output_types
        except AssertionError:
            raise EEACCriticalClusterEvaluatorSequenceException(node_data.id, node_data.name)

        # Create evaluator
        return CriticalClustersEvaluatorNode(
            id=node_data.id,
            name=node_data.name,
            evaluation_tree=evaluation_tree,
            must_display_report=configuration.display_report
        )
