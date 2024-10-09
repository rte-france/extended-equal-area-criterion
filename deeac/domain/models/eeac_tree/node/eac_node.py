# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Union, Type, Optional
import numpy as np

from deeac.domain.exceptions import EEACTreeNodeInputsException, PlotOutputDirectoryException
from deeac.domain.models.omib.omib import OMIBStabilityState
from .eeac_tree_node import EEACTreeNodeIOType, EEACTreeNode, EEACTreeNodeIOs
from deeac.domain.models.omib import OMIB
from deeac.domain.services.eac import EAC
import deeac.domain.ports.dtos.eeac_tree as node_dtos


class EACNodeInputs(EEACTreeNodeIOs):
    """
    Inputs of this node.
    """
    omib: OMIB
    output_dir: Optional[str]


class EACNodeOutputs(EEACTreeNodeIOs):
    """
    Outputs of this node.
    """
    omib: OMIB
    critical_angle: float
    maximum_angle: float


class EACNode(EEACTreeNode):
    """
    Node of and EEAC execution tree representing an EAC instance.
    """

    def __init__(
        self, id: Union[str, int], name: str, angle_increment: float, max_integration_angle: float,
        must_display_report: bool = False, must_plot_area_graph: bool = False
    ):
        """
        Initialize the tree node

        :param id: Unique identifier of the node.
        :param name: Name of the node.
        :param angle_increment: Angle increment (deg) when infering the critical angle.
        :param max_integration_angle: Maximum angle (deg) when integrating the OMIB curve.
        :param must_display_report: True if a report must be outputted for the node.
        :param must_plot_area_graph: True if an area graph must be outputted.
        """
        super().__init__(id, name, must_display_report)

        self._angle_increment = angle_increment
        self._max_integration_angle = max_integration_angle
        self.must_plot_area_graph = must_plot_area_graph

        # Prepare the inputs and outputs
        self._input_types = {EEACTreeNodeIOType.OMIB, EEACTreeNodeIOType.OUTPUT_DIR}
        self._output_types = {
            EEACTreeNodeIOType.OMIB,
            EEACTreeNodeIOType.CRIT_ANGLE,
            EEACTreeNodeIOType.MAX_ANGLE
        }

    @property
    def expected_inputs_dto_type(self) -> Type[EEACTreeNodeIOs]:
        """
        Return the expected type of DTO for the inputs.

        :return: The type of DTO.
        """
        return EACNodeInputs

    @EEACTreeNode.inputs.setter
    def inputs(self, inputs: EEACTreeNodeIOs):
        """
        Provide the inputs to this node.

        :param inputs: Input values.
        :raise EEACTreeNodeInputsException if the input is not expected by this node.
        """
        try:
            assert type(inputs) == EACNodeInputs
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

        # Create instance of EAC service
        angle_increment = np.deg2rad(self._angle_increment)
        max_integration_angle = np.deg2rad(self._max_integration_angle)
        eac = EAC(self._inputs.omib, angle_increment, max_integration_angle)

        # Generate results
        self._outputs = EACNodeOutputs(
            omib=self._inputs.omib,
            critical_angle=eac.critical_clearing_angle,
            maximum_angle=eac.maximum_angle
        )

        # Generate area plot
        if self.must_plot_area_graph:
            if self._inputs.output_dir is None:
                # No output directory, cannot plot
                raise PlotOutputDirectoryException()
            output_dir = self._inputs.output_dir
            output_file = f"{output_dir}/{self.complete_id}_area_plot.pdf"
            eac.generate_area_plot(output_file)

    def _generate_report(self) -> str:
        """
        Generate an output report as a string.
        """
        # Get initial report
        report = super()._generate_report()

        # Configuration
        report = (
            f"{report}\tConfiguration:\n"
            f"\t\tAngle increment: {self._angle_increment} deg\n"
            f"\t\tMaximum OMIB integration angle: {self._max_integration_angle} deg\n"
        )

        # Outputs
        if self.cancelled or self.failed:
            # No output
            return report
        separator = "\n\t\t"
        omib = separator.join(str(self._outputs.omib).split("\n"))
        if self._outputs.omib.stability_state == OMIBStabilityState.POTENTIALLY_STABLE:
            report = (
                f"{report}\tOutputs:\n"
                f"\t\tCritical angle: {round(self._outputs.critical_angle, 3)} rad "
                f"[{round(np.rad2deg(self._outputs.critical_angle), 3)} deg]\n"
                f"\t\tMaximum angle: {round(self._outputs.maximum_angle, 3)} rad "
                f"[{round(np.rad2deg(self._outputs.maximum_angle), 3)} deg]\n"
                f"\t\t{omib}\n"
            )
        else:
            report = (
                f"{report}\tOutputs:\n"
                f"\t\tCritical angle: Not computed as case is not POTENTIALLY STABLE.\n"
                f"\t\t{omib}\n"
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
        EEACTreeNode.validate_configuration(node_data, node_dtos.EACConfiguration)
        configuration = node_data.configuration

        # Create instance
        return EACNode(
            id=node_data.id,
            name=node_data.name,
            angle_increment=configuration.angle_increment,
            max_integration_angle=configuration.max_integration_angle,
            must_display_report=configuration.display_report,
            must_plot_area_graph=configuration.plot_area_graph
        )
