# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import numpy as np
from typing import Union, Type, Optional

from deeac.domain.exceptions import EEACTreeNodeInputsException
from .eeac_tree_node import EEACTreeNodeIOType, EEACTreeNode, EEACTreeNodeIOs, EEACClusterResults
from deeac.domain.models.omib import OMIB, OMIBStabilityState
from deeac.domain.models.rotor_angle_trajectory_calculator import OMIBRotorAngleTrajectoryCalculator
from deeac.domain.models.rotor_angle_trajectory_calculator.taylor_series import OMIBTaylorSeries
from deeac.domain.models.rotor_angle_trajectory_calculator.numerical_integrator import OMIBNumericalIntegrator
import deeac.domain.ports.dtos.eeac_tree as node_dtos


# Mapping between OMIB calculators and their type
OMIBCalculators = {
    node_dtos.OMIBTrajectoryCalculatorType.TAYLOR: OMIBTaylorSeries,
    node_dtos.OMIBTrajectoryCalculatorType.NUMERICAL: OMIBNumericalIntegrator
}


class OMIBTrajectoryCalculatorNodeInputs(EEACTreeNodeIOs):
    """
    Inputs of this node.
    """
    critical_angle: float
    maximum_angle: float
    omib: OMIB
    output_dir: Optional[str]


class OMIBTrajectoryCalculatorNodeOutputs(EEACTreeNodeIOs):
    """
    Outputs of this node.
    """
    cluster_results: EEACClusterResults


class OMIBTrajectoryCalculatorNode(EEACTreeNode):
    """
    Node of and EEAC execution tree representing a generator trajectory calculator.
    """

    def __init__(
        self, id: Union[str, int], name: str, calculator_type: Type[OMIBRotorAngleTrajectoryCalculator],
        critical_angle_shift: float = 0, must_display_report: bool = False
    ):
        """
        Initialize the tree node

        :param id: Unique identifier of the node.
        :param name: Name of the node.
        :param calculator_type: Type of OMIB trajectory calculator.
        :param critical_angle_shift: Positive shift (deg) to apply to the critical angle. It is only used to compute
                                     the times associated to the angles greater than the critical angle, allowing to
                                     obtain an improved curve in further analyses. The time outputted for the
                                     critical angle is not altered by this shift.
        :param must_display_report: True if a report must be outputted for the node
        """
        super().__init__(id, name, must_display_report)

        self._calculator_type = calculator_type
        self._critical_angle_shift = critical_angle_shift

        # Prepare the inputs and outputs
        self._input_types = {
            EEACTreeNodeIOType.CRIT_ANGLE,
            EEACTreeNodeIOType.MAX_ANGLE,
            EEACTreeNodeIOType.OMIB,
            EEACTreeNodeIOType.OUTPUT_DIR
        }
        self._output_types = {EEACTreeNodeIOType.CLUSTER_RESULTS}

        # The central result, CCT or stability
        self.critical_result = None

    @property
    def expected_inputs_dto_type(self) -> Type[EEACTreeNodeIOs]:
        """
        Return the expected type of DTO for the inputs.

        :return: The type of DTO.
        """
        return OMIBTrajectoryCalculatorNodeInputs

    @EEACTreeNode.inputs.setter
    def inputs(self, inputs: EEACTreeNodeIOs):
        """
        Provide the inputs to this node.

        :param inputs: Input values.
        :raise EEACTreeNodeInputsException if the input is not expected by this node.
        """
        try:
            assert type(inputs) == OMIBTrajectoryCalculatorNodeInputs
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

        # Create trajectory calculator
        critical_angle_shift = np.deg2rad(self._critical_angle_shift)
        calculator = self._calculator_type(self._inputs.omib, critical_angle_shift)

        if self._inputs.omib.stability_state == OMIBStabilityState.ALWAYS_STABLE:
            # Case is always stable
            critical_time, maximum_time = np.inf, np.inf
        else:
            # Compute trajectory times for critical and maximum angles
            critical_time, maximum_time = calculator.get_trajectory_times(
                angles=[self._inputs.critical_angle, self._inputs.maximum_angle],
                transition_angle=self._inputs.critical_angle
            )

        # A critical time beyond 1s is meaningless
        if critical_time > 1:
            critical_time, maximum_time = np.inf, np.inf
            self._inputs.omib.stability_state = OMIBStabilityState.ALWAYS_STABLE


        # Generate output
        generators = self._inputs.omib.critical_cluster.generators.union(
            self._inputs.omib.non_critical_cluster.generators
        )
        self._outputs = OMIBTrajectoryCalculatorNodeOutputs(
            cluster_results=EEACClusterResults(
                critical_angle=self._inputs.critical_angle,
                critical_time=critical_time,
                maximum_angle=self._inputs.maximum_angle,
                maximum_time=maximum_time,
                critical_cluster=self._inputs.omib.critical_cluster,
                non_critical_cluster=self._inputs.omib.non_critical_cluster,
                dynamic_generators=generators,
                omib_stability_state=self._inputs.omib.stability_state,
                omib_swing_state=self._inputs.omib.swing_state
            )
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
            f"\t\tType of calculator: {self._calculator_type.__name__}\n"
            f"\t\tCritical angle shift: {self._critical_angle_shift} deg\n"
        )

        # Inputs
        if self._inputs is not None:
            separator = "\n\t\t"
            omib = separator.join(str(self._inputs.omib).split("\n"))
            if self._inputs.omib.stability_state == OMIBStabilityState.POTENTIALLY_STABLE:
                report = (
                    f"{report}\tInputs:\n"
                    f"\t\tCritical angle: {round(self._inputs.critical_angle, 3)} rad "
                    f"[{round(np.rad2deg(self._inputs.critical_angle), 3)} deg]\n"
                    f"\t\tMaximum angle: {round(self._inputs.maximum_angle, 3)} rad "
                    f"[{round(np.rad2deg(self._inputs.maximum_angle), 3)} deg]\n"
                    f"\t\t{omib}\n"
                )
            else:
                report = (
                    f"{report}\tInputs:\n"
                    f"\t\t{omib}\n"
                )
        # Outputs
        if self.cancelled or self.failed:
            # No output
            return report
        critical_generators = ", ".join(
            sorted(gen.name for gen in self._outputs.cluster_results.critical_cluster.generators)
        )
        generators = ", ".join(sorted(gen.name for gen in self._outputs.cluster_results.dynamic_generators))

        if self._inputs.omib.stability_state == OMIBStabilityState.POTENTIALLY_STABLE:
            report = (
                f"{report}\tOutputs:\n"
                f"\t\tGenerators: {generators}\n"
                f"\t\tCritical cluster: {critical_generators}\n"
                f"\t\tCritical angle: {round(self._inputs.critical_angle, 3)} rad "
                f"[{round(np.rad2deg(self._inputs.critical_angle), 3)} deg]\n"
                f"\t\tCritical time: {round(self._outputs.cluster_results.critical_time * 1000, 3)} ms\n"
                f"\t\tMaximum angle: {round(self._inputs.maximum_angle, 3)} rad "
                f"[{round(np.rad2deg(self._inputs.maximum_angle), 3)} deg]\n"
                f"\t\tMaximum time: {round(self._outputs.cluster_results.maximum_time * 1000, 3)} ms\n"
                f"\t\tOMIB stability state: {self._inputs.omib.stability_state.value}\n"
                f"\t\tOMIB swing state: {self._inputs.omib.swing_state.value}"
            )
        else:
            report = (
                f"{report}\tOutputs:\n"
                f"\t\tGenerators: {generators}\n"
                f"\t\tCritical cluster: {critical_generators}\n"
                f"\t\tOMIB stability state: {self._inputs.omib.stability_state.value}\n"
                f"\t\tOMIB swing state: {self._inputs.omib.swing_state.value}\n"
                f"\t\tCritical time: Not computed as case is not POTENTIALLY STABLE."
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
        EEACTreeNode.validate_configuration(node_data, node_dtos.OMIBTrajectoryCalculatorConfiguration)
        configuration = node_data.configuration

        # Create instance
        return OMIBTrajectoryCalculatorNode(
            id=node_data.id,
            name=node_data.name,
            calculator_type=OMIBCalculators[configuration.calculator_type],
            critical_angle_shift=configuration.critical_angle_shift,
            must_display_report=configuration.display_report
        )
