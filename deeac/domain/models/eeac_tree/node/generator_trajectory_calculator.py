# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import numpy as np
from typing import Union, Type, Set, Optional, List

from deeac.domain.exceptions import EEACTreeNodeInputsException, PlotOutputDirectoryException
from .eeac_tree_node import EEACTreeNodeIOType, EEACTreeNode, EEACTreeNodeIOs, EEACClusterResults
from deeac.domain.models.rotor_angle_trajectory_calculator.taylor_series import GeneratorTaylorSeries
from deeac.domain.models import GeneratorCluster, DynamicGenerator, Network
from deeac.domain.models.omib import OMIBStabilityState
import deeac.domain.ports.dtos.eeac_tree as node_dtos


class GeneratorTrajectoryCalculatorNodeInputs(EEACTreeNodeIOs):
    """
    Inputs of this node.
    """
    network: Network
    cluster_results: EEACClusterResults
    output_dir: Optional[str]


class GeneratorTrajectoryCalculatorNodeOutputs(EEACTreeNodeIOs):
    """
    Outputs of this node.
    """
    critical_cluster: GeneratorCluster
    non_critical_cluster: GeneratorCluster
    dynamic_generators: Set[DynamicGenerator]


class GeneratorTrajectoryCalculatorNode(EEACTreeNode):
    """
    Node of and EEAC execution tree representing a generator trajectory calculator.
    """

    def __init__(
        self, id: Union[str, int], name: str, number_during_fault_intervals: int, number_post_fault_intervals: int,
        critical_time_shift: float = 0, must_display_report: bool = False, generators_to_plot: List[str] = None
    ):
        """
        Initialize the tree node

        :param id: Unique identifier of the node.
        :param name: Name of the node.
        :param number_during_fault_intervals: Number of intervals to consider in the during-fault state.
        :param number_post_fault_intervals: Number of intervals to consider in the post-fault state.
        :param critical_time_shift: Positive shift (ms) to apply to the critical time. It is only used to compute
                                    the rotor angles after the critical time, allowing to obtain improved curves in
                                    further analyses. The angle outputted for the critical time is not altered by
                                    this shift.
        :param must_display_report: True if a report must be outputted for the node.
        :param generators_to_plot: List of generator names whose angle evolution must be plotted.
                                   None means no plot, while an empty list corresponds to all generators.
        """
        super().__init__(id, name, must_display_report)

        self._nb_during_fault_intervals = number_during_fault_intervals
        self._nb_post_fault_intervals = number_post_fault_intervals
        self._critical_time_shift = critical_time_shift
        self._generators_to_plot = generators_to_plot

        # Prepare the inputs and outputs
        self._input_types = {
            EEACTreeNodeIOType.NETWORK,
            EEACTreeNodeIOType.CLUSTER_RESULTS,
            EEACTreeNodeIOType.OUTPUT_DIR
        }
        self._output_types = {
            EEACTreeNodeIOType.CRIT_CLUSTER,
            EEACTreeNodeIOType.NON_CRIT_CLUSTER,
            EEACTreeNodeIOType.DYNAMIC_GENERATORS
        }

    @property
    def expected_inputs_dto_type(self) -> Type[EEACTreeNodeIOs]:
        """
        Return the expected type of DTO for the inputs.

        :return: The type of DTO.
        """
        return GeneratorTrajectoryCalculatorNodeInputs

    @EEACTreeNode.inputs.setter
    def inputs(self, inputs: EEACTreeNodeIOs):
        """
        Provide the inputs to this node.

        :param inputs: Input values.
        :raise EEACTreeNodeInputsException if the input is not expected by this node.
        """
        try:
            assert type(inputs) == GeneratorTrajectoryCalculatorNodeInputs
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

        # State must be potentially stable
        if self._inputs.cluster_results.omib_stability_state != OMIBStabilityState.POTENTIALLY_STABLE:
            self.cancel(cancel_msg="EAC state is not POTENTIALLY STABLE.")

        # Create trajectory calculator
        critical_time_shift = self._critical_time_shift / 1000.0
        calculator = GeneratorTaylorSeries(self._inputs.network, critical_time_shift)

        # Compute trajectory for each generator
        calculator.update_generator_angles(
            generators=self._inputs.cluster_results.dynamic_generators,
            transition_time=self._inputs.cluster_results.critical_time,
            last_update_time=self._inputs.cluster_results.maximum_time,
            number_during_fault_intervals=self._nb_during_fault_intervals,
            number_post_fault_intervals=self._nb_post_fault_intervals
        )

        # Update generator angles
        self._outputs = GeneratorTrajectoryCalculatorNodeOutputs(
            critical_cluster=self._inputs.cluster_results.critical_cluster,
            non_critical_cluster=self._inputs.cluster_results.non_critical_cluster,
            dynamic_generators=self._inputs.cluster_results.dynamic_generators
        )

        # Plot rotor angles if needed
        if self._generators_to_plot is not None:
            if self._inputs.output_dir is None:
                # No output directory, cannot plot
                raise PlotOutputDirectoryException()
            generators = [gen for gen in self._inputs.cluster_results.dynamic_generators]
            if len(self._generators_to_plot) > 0:
                # Limited plot
                generators = {gen for gen in generators if gen.name in self._generators_to_plot}
            output_dir = self._inputs.output_dir
            output_file = f"{output_dir}/{self.complete_id}_rotor_angles_plot.pdf"
            calculator.generate_generator_angles_plot(generators, output_file)

    def _generate_report(self) -> str:
        """
        Generate an output report as a string.
        """
        # Get initial report
        report = super()._generate_report()

        # Configuration
        report = (
            f"{report}\tConfiguration:\n"
            f"\t\tNumber of during-fault intervals: {self._nb_during_fault_intervals}\n"
            f"\t\tNumber of post-fault intervals: {self._nb_post_fault_intervals}\n"
            f"\t\tCritical time shift: {self._critical_time_shift} ms\n"
        )

        # Inputs
        if self._inputs is not None:
            critical_generators = ", ".join(
                sorted(gen.name for gen in self._inputs.cluster_results.critical_cluster.generators)
            )
            if self._inputs.cluster_results.omib_stability_state == OMIBStabilityState.POTENTIALLY_STABLE:
                report = (
                    f"{report}\tInputs:\n"
                    f"\t\tCritical generators: {critical_generators}\n"
                    f"\t\tCritical angle: {round(self._inputs.cluster_results.critical_angle, 3)} rad "
                    f"[{round(np.rad2deg(self._inputs.cluster_results.critical_angle), 3)} deg]\n"
                    f"\t\tCritical time: {round(self._inputs.cluster_results.critical_time * 1000, 3)} ms\n"
                    f"\t\tMaximum angle: {round(self._inputs.cluster_results.maximum_angle, 3)} rad "
                    f"[{round(np.rad2deg(self._inputs.cluster_results.maximum_angle), 3)} deg]\n"
                    f"\t\tMaximum time: {round(self._inputs.cluster_results.maximum_time * 1000, 3)} ms\n"
                    f"\t\tOMIB stability state: {self._inputs.cluster_results.omib_stability_state.value}\n"
                    f"\t\tOMIB swing state: {self._inputs.cluster_results.omib_swing_state.value}\n"
                )
            else:
                report = (
                    f"{report}\tInputs:\n"
                    f"\t\tCritical generators: {critical_generators}\n"
                    f"\t\tOMIB stability state: {self._inputs.cluster_results.omib_stability_state.value}\n"
                    f"\t\tOMIB swing state: {self._inputs.cluster_results.omib_swing_state.value}\n"
                )
        # Outputs
        if self.cancelled or self.failed:
            # No output
            return report
        generators = ", ".join(sorted(gen.name for gen in self._outputs.dynamic_generators))
        generator = next(gen for gen in self._outputs.dynamic_generators)
        update_times = ", ".join([str(round(time * 1000, 3)) for time in generator.observation_times])
        report = (
            f"{report}\tOutput:\n"
            f"\t\tUpdated generators: {generators}\n"
            f"\t\tUpdate times (ms): {update_times}\n"
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
        EEACTreeNode.validate_configuration(node_data, node_dtos.GeneratorTrajectoryCalculatorConfiguration)
        configuration = node_data.configuration

        # Get list of generators to plot
        generators_to_plot = configuration.generators_to_plot
        if generators_to_plot == node_dtos.Uncountable.ALL:
            generators_to_plot = []
        elif generators_to_plot == node_dtos.Uncountable.NONE:
            generators_to_plot = None

        # Create instance
        return GeneratorTrajectoryCalculatorNode(
            id=node_data.id,
            name=node_data.name,
            number_during_fault_intervals=configuration.nb_during_fault_intervals,
            number_post_fault_intervals=configuration.nb_post_fault_intervals,
            critical_time_shift=configuration.critical_time_shift,
            must_display_report=configuration.display_report,
            generators_to_plot=generators_to_plot
        )
