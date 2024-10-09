# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import os
import json

from typing import Dict, Any
from pydantic import ValidationError

from deeac.domain.exceptions import EEACTreeNodeInputsException
from deeac.domain.models.eeac_tree import EEACTree
from deeac.domain.models import Network
from deeac.domain.models.eeac_tree import EEACTreeNodeIOType


class EEAC:
    """
    Service able to apply the Extended Equal Area Criterion (EAC) to determine the critical clearing angle and time of
    a power system in a transient stability study based on an execution tree.
    """

    def __init__(self, execution_tree: EEACTree, network: Network, output_dir: str = None, warn: bool = False):
        """
        Initialize the EAC service.

        :param execution_tree: EEAC tree used as execution tree.
        :param network: Network to which EEAC must be applied.
        :param output_dir: Path to an output directory, if node results must be outputted in files.
        :param warn: warning if there's a failing critical cluster candidate
        """
        self._execution_tree = execution_tree
        self._network = network
        self._output_dir = output_dir
        self._inputs = None
        self._warn = warn
        self.critical_result = list()

    def provide_inputs(self, inputs: Dict[EEACTreeNodeIOType, Any]):
        """
        Provide the inputs to the EEAC service.
        The inputs are provided as a dictionary, because the first node executed by EEAC may differ depending on the
        execution tree. The inputs may therefore differ according to the tree.

        :param inputs: Inputs to provide to the service.
        :raise EEACTreeNodeInputsException if the inputs are invalid for the first node.
        """
        inputs_dict = {io_type.value: input_value for io_type, input_value in inputs.items()}

        # Get output directory and create it if required
        if EEACTreeNodeIOType.OUTPUT_DIR.value in inputs_dict:
            # Take directory in inputs if exists
            self._output_dir = inputs_dict[EEACTreeNodeIOType.OUTPUT_DIR.value]
        if self._output_dir is not None:
            # Create directory
            os.makedirs(self._output_dir, exist_ok=True)

        # Add directory and network, so that they are passed to the node if required
        inputs_dict[EEACTreeNodeIOType.OUTPUT_DIR.value] = self._output_dir
        inputs_dict[EEACTreeNodeIOType.NETWORK.value] = self._network

        # Get expected input DTO of first node
        inputs_dto_type = self._execution_tree.root.expected_inputs_dto_type
        try:
            self._inputs = inputs_dto_type(**inputs_dict)
        except ValidationError:
            raise EEACTreeNodeInputsException(self._execution_tree.root)

    def run(self):
        """
        Run EEAC according to the execution tree.
        """
        # Deep first traversal of the tree
        nodes = self._execution_tree.deep_first_traversal()

        # Run root node
        self._execution_tree.root.inputs = self._inputs
        self._execution_tree.root.run()

        report = str()

        # Go through other nodes
        for node in nodes[1:]:
            # Get parent node (only one parent per node)
            parent_node = self._execution_tree.predecessor(node)
            # Check if parent node encountered problems
            if parent_node.cancelled:
                # Cannot run the node
                node.cancel(cancel_msg="Execution of parent node was cancelled.", log_dir=self._output_dir)
            elif parent_node.failed:
                # Cannot run the node
                node.cancel(cancel_msg="Execution of parent node failed.", log_dir=self._output_dir)
            else:
                # Get inputs DTO
                inputs_dto_type = node.expected_inputs_dto_type
                # Provide inputs adding network and output directory
                inputs_dict = parent_node.outputs.dict()
                inputs_dict[EEACTreeNodeIOType.OUTPUT_DIR.value] = self._output_dir
                inputs_dict[EEACTreeNodeIOType.NETWORK.value] = self._network
                # EEACTree guarantees that the inputs and outputs are compatible, no error should occur
                node.inputs = inputs_dto_type(**inputs_dict)
            # Run
            results = node.run()
            if isinstance(results, str):
                report += results
            else:
                node_report, self.critical_result = results
                report += node_report

            # If it is a node with a critical result
            if hasattr(node, 'critical_result'):
                # Save essential results of the last node in JSON file
                if node.critical_result:
                    self.critical_result.append(node.critical_result)

                # Save essential results of the last node in JSON file
                if hasattr(node, "_failed_clusters") and \
                        node._failed_clusters is not None and len(node._failed_clusters) > 0:
                    failures = [str(i) for i in node._failed_clusters]
                    message = f"{len(failures)} failed candidates: {', '.join(failures)}"
                    self.critical_result.append({"warning": message})
                    print(message)

        return report

    def reset(self):
        """
        Reset the execution tree, deleting the inputs, outputs and state for each node.
        """
        for node in self._execution_tree.deep_first_traversal():
            node.reset()
