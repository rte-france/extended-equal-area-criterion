# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import numpy as np
from typing import Union, Type, Iterator, Optional, Dict, Tuple
from itertools import tee

from deeac.domain.exceptions import EEACTreeNodeInputsException
from deeac.domain.models.omib import OMIBStabilityState
from .eeac_tree_node import EEACTreeNodeIOType, EEACTreeNode, EEACTreeNodeIOs, EEACClusterResults
from deeac.domain.services.critical_cluster_selector import (
    CriticalClusterSelector, MinCriticalClusterSelector, CriticalClusterResults
)
import deeac.domain.ports.dtos.eeac_tree as node_dtos


# Mapping between critical clusters identifiers and their types
CCSelectors = {
    node_dtos.CriticalClusterSelectorType.MIN: MinCriticalClusterSelector
}


class CriticalClusterSelectorNodeInputs(EEACTreeNodeIOs):
    """
    Inputs of this node.
    """
    cluster_results_iterator: Iterator[EEACClusterResults]
    output_dir: Optional[str]


class CriticalClusterSelectorNodeOutputs(EEACTreeNodeIOs):
    """
    Outputs of this node.
    """
    cluster_results: EEACClusterResults


class CriticalClusterSelectorNode(EEACTreeNode):
    """
    Node of and EEAC execution tree representing an EAC instance.
    """

    def __init__(
        self, id: Union[str, int], name: str, selector_type: Type[CriticalClusterSelector],
        must_display_report: bool = False
    ):
        """
        Initialize the tree node

        :param id: Unique identifier of the node.
        :param name: Name of the node.
        :param selector_type: Type of critical cluster selector.
        :param must_display_report: True if a report must be outputted for the node.
        """
        super().__init__(id, name, must_display_report)

        self._selector_type = selector_type

        # Prepare the inputs and outputs
        self._input_types = {EEACTreeNodeIOType.CLUSTER_RESULTS_ITERATOR, EEACTreeNodeIOType.OUTPUT_DIR}
        self._output_types = {EEACTreeNodeIOType.CLUSTER_RESULTS}

        # The central result, CCT or stability
        self.critical_result = None

    @property
    def expected_inputs_dto_type(self) -> Type[EEACTreeNodeIOs]:
        """
        Return the expected type of DTO for the inputs.

        :return: The type of DTO.
        """
        return CriticalClusterSelectorNodeInputs

    @EEACTreeNode.inputs.setter
    def inputs(self, inputs: EEACTreeNodeIOs):
        """
        Provide the inputs to this node.

        :param inputs: Input values.
        :raise EEACTreeNodeInputsException if the input is not expected by this node.
        """
        try:
            assert type(inputs) == CriticalClusterSelectorNodeInputs
            self._inputs = inputs
        except AssertionError:
            raise EEACTreeNodeInputsException(self)

    def can_be_leaf(self) -> bool:
        """
        Determine if the node can be a leaf in the tree.

        :return: True if the node can be a leaf, False otherwise.
        """
        return True

    def _run(self):
        """
        Run the node in order to produce the output values.

        :raise: A DEEACException in case of errors.
        """
        # Verify inputs
        self._verify_inputs()

        # Create selector inputs
        cluster_results_iterator, self._inputs.cluster_results_iterator = tee(self._inputs.cluster_results_iterator)
        cluster_results = []
        clusters = []
        for results in cluster_results_iterator:
            cluster_results.append(results)
            clusters.append(CriticalClusterResults(**results.dict()))

        # Select cluster
        cluster_id = self._selector_type.select_cluster(clusters)

        # Generate results
        self._outputs = CriticalClusterSelectorNodeOutputs(
            cluster_results=cluster_results[cluster_id]
        )

    def _generate_report(self) -> str:
        """
        Generate an output report as a string.
        """
        # Get initial report
        report = super()._generate_report()

        # Configuration
        report = (
            f"{report}\tConfiguration:\n"
            f"\t\tType of selector: {self._selector_type.__name__}\n"
        )

        # Inputs
        if self._inputs is not None:
            self._inputs.cluster_results_iterator, cluster_results_iterator = tee(self._inputs.cluster_results_iterator)
            report = f"{report}\tInputs:\n"
            for cluster_nb, results in enumerate(cluster_results_iterator):
                generator_names = sorted(gen.name for gen in results.critical_cluster.generators)
                critical_generators = ", ".join(generator_names)
                if results.omib_stability_state == OMIBStabilityState.POTENTIALLY_STABLE:
                    report = (
                        f"{report}\t\tCluster {cluster_nb}:\n"
                        f"\t\t\tCritical generators: {critical_generators}\n"
                        f"\t\t\tCritical angle: {round(results.critical_angle, 3)} rad "
                        f"[{round(np.rad2deg(results.critical_angle), 3)} deg]\n"
                        f"\t\t\tCritical time: {round(results.critical_time * 1000, 3)} ms\n"
                        f"\t\t\tMaximum angle: {round(results.maximum_angle, 3)} rad "
                        f"[{round(np.rad2deg(results.maximum_angle), 3)} deg]\n"
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

        # Outputs
        if self.failed:
            # No output
            self.critical_result = {"status": "failed"}
            return report

        elif self.cancelled:
            # No output
            self.critical_result = {"status": "cancelled"}
            return report

        results = self._outputs.cluster_results
        generators = ", ".join(sorted(gen.name for gen in results.critical_cluster.generators))
        self.critical_result = {
            "status": results.omib_stability_state.value,
            "swing_state": results.omib_swing_state.value,
            "critical_cluster": generators,
            "node_id": self.id
        }
        if results.omib_stability_state == OMIBStabilityState.POTENTIALLY_STABLE:
            self.critical_result["CCT"] = results.critical_time
            report = (
                f"{report}\tOutputs:\n"
                f"\t\tCritical generators: {generators}\n"
                f"\t\tCritical angle: {round(results.critical_angle, 3)} rad "
                f"[{round(np.rad2deg(results.critical_angle), 3)} deg]\n"
                f"\t\tCritical time: {round(results.critical_time * 1000, 3)} ms\n"
                f"\t\tMaximum angle: {round(results.maximum_angle, 3)} rad "
                f"[{round(np.rad2deg(results.maximum_angle), 3)} deg]\n"
                f"\t\tMaximum time: {round(results.maximum_time * 1000, 3)} ms\n"
                f"\t\tOMIB stability state: {results.omib_stability_state.value}\n"
                f"\t\tOMIB swing state: {results.omib_swing_state.value}"
            )
        else:
            report = (
                f"{report}\tOutputs:\n"
                f"\t\tCritical generators: {generators}\n"
                f"\t\tOMIB stability state: {results.omib_stability_state.value}\n"
                f"\t\tOMIB swing state: {results.omib_swing_state.value}"
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
        EEACTreeNode.validate_configuration(node_data, node_dtos.CriticalClusterSelectorConfiguration)
        configuration = node_data.configuration

        # Convert critical cluster selector type
        cc_selector_type = CCSelectors[configuration.selector_type]

        # Create instance
        return CriticalClusterSelectorNode(
            id=node_data.id,
            name=node_data.name,
            selector_type=cc_selector_type,
            must_display_report=configuration.display_report
        )
