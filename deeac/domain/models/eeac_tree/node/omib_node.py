# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Union, Type, Optional

from deeac.domain.exceptions import EEACTreeNodeInputsException
from .eeac_tree_node import EEACTreeNodeIOType, EEACTreeNode, EEACTreeNodeIOs
from deeac.domain.models import Network, GeneratorCluster
from deeac.domain.models.omib import OMIB, ZOOMIB, RevisedZOOMIB, COOMIB, RevisedCOOMIB, DOMIB, RevisedDOMIB
import deeac.domain.ports.dtos.eeac_tree as node_dtos


# Mapping between OMIBs and their types
OMIBs = {
    node_dtos.OMIBType.ZOOMIB: ZOOMIB,
    node_dtos.OMIBType.RZOOMIB: RevisedZOOMIB,
    node_dtos.OMIBType.COOMIB: COOMIB,
    node_dtos.OMIBType.RCOOMIB: RevisedCOOMIB,
    node_dtos.OMIBType.DOMIB: DOMIB,
    node_dtos.OMIBType.RDOMIB: RevisedDOMIB,
}


class OMIBNodeInputs(EEACTreeNodeIOs):
    """
    Inputs of this node.
    """
    network: Network
    critical_cluster: GeneratorCluster
    non_critical_cluster: GeneratorCluster
    output_dir: Optional[str]


class OMIBNodeOutputs(EEACTreeNodeIOs):
    """
    Outputs of this node.
    """
    omib: OMIB


class OMIBNode(EEACTreeNode):
    """
    Node of and EEAC execution tree representing an OMIB instance.
    """

    def __init__(self, id: Union[str, int], name: str, omib_type: Type[OMIB], must_display_report: bool = False):
        """
        Initialize the tree node

        :param id: Unique identifier of the node.
        :param name: Name of the node.
        :param omib_type: Type of OMIB.
        :param must_display_report: True if a report must be outputted for the node.
        """
        super().__init__(id, name, must_display_report)
        self._omib_type = omib_type

        # Prepare the inputs and outputs
        self._input_types = {
            EEACTreeNodeIOType.NETWORK,
            EEACTreeNodeIOType.CRIT_CLUSTER,
            EEACTreeNodeIOType.NON_CRIT_CLUSTER,
            EEACTreeNodeIOType.OUTPUT_DIR}
        self._output_types = {EEACTreeNodeIOType.OMIB}

    @property
    def expected_inputs_dto_type(self) -> Type[EEACTreeNodeIOs]:
        """
        Return the expected type of DTO for the inputs.

        :return: The type of DTO.
        """
        return OMIBNodeInputs

    @EEACTreeNode.inputs.setter
    def inputs(self, inputs: EEACTreeNodeIOs):
        """
        Provide the inputs to this node.

        :param inputs: Input values.
        :raise EEACTreeNodeInputsException if the input is not expected by this node.
        """
        try:
            assert type(inputs) == OMIBNodeInputs
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

        # Create instance of OMIB
        omib = self._omib_type(
            network=self._inputs.network,
            critical_cluster=self._inputs.critical_cluster,
            non_critical_cluster=self._inputs.non_critical_cluster
        )

        # Generate results
        self._outputs = OMIBNodeOutputs(omib=omib)

    def _generate_report(self) -> str:
        """
        Generate an output report as a string.
        """
        # Get initial report
        report = super()._generate_report()

        # Configuration
        report = (
            f"{report}\tConfiguration:\n"
            f"\t\tType of OMIB: {self._omib_type.__name__}\n"
        )

        # Outputs
        if self.cancelled or self.failed:
            # No output
            return report
        separator = "\n\t\t"
        omib = separator.join(str(self._outputs.omib).split("\n"))
        report = (
            f"{report}\tOutput:\n\t\t{omib}"
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
        EEACTreeNode.validate_configuration(node_data, node_dtos.OMIBConfiguration)
        configuration = node_data.configuration

        # Convert OMIB type
        omib_type = OMIBs[configuration.omib_type]

        # Create instance
        return OMIBNode(
            id=node_data.id,
            name=node_data.name,
            omib_type=omib_type
        )
