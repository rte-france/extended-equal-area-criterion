# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import re
from typing import Union, List, Set, Iterator, Tuple, Type, Optional
from itertools import tee

import numpy as np

from deeac.domain.exceptions import EEACTreeNodeInputsException
from .eeac_tree_node import EEACTreeNodeIOType, EEACTreeNode, EEACTreeNodeIOs
from deeac.domain.services.critical_clusters_identifier import (
    AccelerationCriticalClustersIdentifier, CompositeCriticalClustersIdentifier, TrajectoryCriticalClustersIdentifier,
    ConstrainedCriticalClustersIdentifier, CriticalClustersIdentifier, DuringFaultTrajectoryCriticalClustersIdentifier
)
from deeac.domain.models import Network, DynamicGenerator, GeneratorCluster, Value, Unit, PUBase
from deeac.domain.services.factories import CriticalClustersIdentifierFactory
import deeac.domain.ports.dtos.eeac_tree as node_dtos


# Mapping between critical clusters identifiers and their types
CCIdentifiers = {
    node_dtos.CriticalClustersIdentifierType.ACCELERATION: AccelerationCriticalClustersIdentifier,
    node_dtos.CriticalClustersIdentifierType.COMPOSITE: CompositeCriticalClustersIdentifier,
    node_dtos.CriticalClustersIdentifierType.TRAJECTORY: TrajectoryCriticalClustersIdentifier,
    node_dtos.CriticalClustersIdentifierType.CONSTRAINED: ConstrainedCriticalClustersIdentifier,
    node_dtos.CriticalClustersIdentifierType.DURING_FAULT_TRAJECTORY: DuringFaultTrajectoryCriticalClustersIdentifier
}


POWER_PATTERN = re.compile("^(\d*\.{0,1}\d+)\s*(MW|kW|W)$")


class CriticalClustersIdentifierNodeInputs(EEACTreeNodeIOs):
    """
    Inputs of this node.
    """
    network: Network
    dynamic_generators: Set[DynamicGenerator]
    output_dir: Optional[str]


class CriticalClustersIdentifierNodeOutputs(EEACTreeNodeIOs):
    """
    Outputs of this node.
    """
    clusters_iterator: Iterator[Tuple[GeneratorCluster, GeneratorCluster]]


class CriticalClustersIdentifierNode(EEACTreeNode):
    """
    Node of and EEAC execution tree representing a critical clusters identifier.
    """

    def __init__(
        self, id: Union[str, int], name: str, identifier_type: Type[CriticalClustersIdentifier], threshold: float,
        threshold_decrement: float, max_number_candidates: int, critical_generator_names: List[str],
        observation_moment_id: int, min_cluster_power: Value = None, must_display_report: bool = False,
        during_fault_identification_time_step: float = None, during_fault_identification_plot_times: List = None,
        significant_angle_variation_threshold: float = None,
        try_all_combinations: bool = False, never_critical_generators: list = None, tso_customization: str = "default"
    ):
        """
        Initialize the tree node

        :param id: Unique identifier of the node.
        :param name: Name of the node.
        :param identifier_type: Type of critical cluster identifier.
        :param threshold: Threshold (between 0 and 1) used to determine the critical generators when comparing criteria.
        :param threshold_decrement: Value to subtract to the threshold in case the critical machine candidates are not
                                    able to provide the minimum active power for the cluster. The subtraction may be
                                    performed multiple times until finding a cluster that meets the minimal aggregated
                                    power.
        :param max_number_candidates: Maximum number of cluster candidates.
        :param critical_generator_names: Names of the critical generators in case of constrained identifier.
        :param observation_moment_id: Identifier of the observation moment in case of trajectory identifier.
        :param min_cluster_power: Minimum aggregated active power a cluster must deliver to be considered as a
                                  potential critical cluster candidate. If None, the aggregated power is not considered.
        :param must_display_report: True if a report must be outputted for the node.
        :param during_fault_identification_time_step: Time in milliseconds to compute the angle using
                                                      Taylor series to identify the critical cluster.
        :param during_fault_identification_plot_times: Times in milliseconds to plot the angles using Taylor series.
        :param significant_angle_variation_threshold: Angle in degrees (positive value expected).
                                                      Enables to detect faults that have negligible consequences
                                                      on the dynamic generators
        :param try_all_combinations: Whether to create a new candidate cluster by removing generators one by one
                                     or to try all combinations of generators
        :param tso_customization: whether to use the default working of an identifier
        or a version meant for a specific network
        :param never_critical_generators: the generators that must be excluded from the critical cluster identification
        """
        super().__init__(id, name, must_display_report)

        self._identifier_type = identifier_type
        self._threshold = threshold
        self._max_number_candidates = max_number_candidates
        self._critical_generator_names = critical_generator_names
        self._observation_moment_id = observation_moment_id
        self._min_cluster_power = min_cluster_power
        self._threshold_decrement = threshold_decrement
        self._during_fault_identification_time_step = during_fault_identification_time_step
        self._during_fault_identification_plot_times = during_fault_identification_plot_times
        self._significant_angle_variation_threshold = significant_angle_variation_threshold
        self._try_all_combinations = try_all_combinations
        self._tso_customization = tso_customization
        self._never_critical_generators = never_critical_generators

        # Prepare the inputs and outputs
        self._candidate_clusters = list()
        self._input_types = {
            EEACTreeNodeIOType.NETWORK,
            EEACTreeNodeIOType.DYNAMIC_GENERATORS,
            EEACTreeNodeIOType.OUTPUT_DIR
        }
        self._output_types = {EEACTreeNodeIOType.CLUSTERS_ITERATOR}

    @property
    def expected_inputs_dto_type(self) -> Type[EEACTreeNodeIOs]:
        """
        Return the expected type of DTO for the inputs.

        :return: The type of DTO.
        """
        return CriticalClustersIdentifierNodeInputs

    @EEACTreeNode.inputs.setter
    def inputs(self, inputs: EEACTreeNodeIOs):
        """
        Provide the inputs to this node.

        :param inputs: Input values.
        :raise EEACTreeNodeInputsException if the input is not expected by this node.
        """
        try:
            assert type(inputs) == CriticalClustersIdentifierNodeInputs
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
        self._candidate_clusters = list()

        # Get minimum aggregated power
        min_cluster_power = None
        if self._min_cluster_power is not None:
            self._min_cluster_power.base = PUBase(self._inputs.network.base_power.to_unit(Unit.MVA), Unit.MW)
            min_cluster_power = self._min_cluster_power.per_unit

        if self._tso_customization == "RTE":
            # Create critical clusters identifier
            critical_cluster_identifier_no_hydro = CriticalClustersIdentifierFactory.get_identifier(
                network=self._inputs.network,
                generators=self._inputs.dynamic_generators,
                cc_identifier_type=self._identifier_type,
                threshold=self._threshold,
                min_cluster_power=min_cluster_power,
                threshold_decrement=self._threshold_decrement,
                critical_generator_names=self._critical_generator_names,
                maximum_number_candidates=self._max_number_candidates,
                observation_moment_id=self._observation_moment_id,
                during_fault_identification_time_step=self._during_fault_identification_time_step,
                during_fault_identification_plot_times=self._during_fault_identification_plot_times,
                significant_angle_variation_threshold=self._significant_angle_variation_threshold,
                try_all_combinations=self._try_all_combinations,
                tso_customization="NO_HYDRO",
                never_critical_generators=self._never_critical_generators
            )

            candidates_no_hydro = list(critical_cluster_identifier_no_hydro.candidate_clusters)
            self._candidate_clusters += candidates_no_hydro
            # Create critical clusters identifier
            critical_cluster_identifier_nuclear = CriticalClustersIdentifierFactory.get_identifier(
                network=self._inputs.network,
                generators=self._inputs.dynamic_generators,
                cc_identifier_type=self._identifier_type,
                threshold=self._threshold,
                min_cluster_power=min_cluster_power,
                threshold_decrement=self._threshold_decrement,
                critical_generator_names=self._critical_generator_names,
                maximum_number_candidates=self._max_number_candidates,
                observation_moment_id=self._observation_moment_id,
                during_fault_identification_time_step=self._during_fault_identification_time_step,
                during_fault_identification_plot_times=self._during_fault_identification_plot_times,
                significant_angle_variation_threshold=self._significant_angle_variation_threshold,
                try_all_combinations=self._try_all_combinations,
                tso_customization="NUCLEAR",
                never_critical_generators=self._never_critical_generators
            )

            candidates_nuclear = list(critical_cluster_identifier_nuclear.candidate_clusters)
            self._candidate_clusters += candidates_nuclear
            unique_candidates = list()
            unique_generators = list()

            for candidate in self._candidate_clusters:
                names = {i.name for i in candidate[0].generators}
                if names in unique_generators:
                    continue
                unique_candidates.append(candidate)
                unique_generators.append(names)

            order = np.argsort([len(j) for j in unique_generators])
            self._candidate_clusters = [unique_candidates[i] for i in order]

            if self._max_number_candidates > 0 and len(self._candidate_clusters) > self._max_number_candidates:
                self._candidate_clusters = self._candidate_clusters[:self._max_number_candidates]

            if self._identifier_type == DuringFaultTrajectoryCriticalClustersIdentifier:
                self._max_angle_at_dft_identification_time = critical_cluster_identifier_no_hydro._max_angle_at_dft_identification_time

                if self._significant_angle_variation_threshold is not None:
                    angle_variation_is_negligible = self._max_angle_at_dft_identification_time <= self._significant_angle_variation_threshold
                    if angle_variation_is_negligible:
                        self._candidate_clusters = [self._candidate_clusters[0]]

            self._outputs = CriticalClustersIdentifierNodeOutputs(clusters_iterator=tee(self._candidate_clusters, 1)[0])
        else:
            # Create critical clusters identifier
            critical_cluster_identifier = CriticalClustersIdentifierFactory.get_identifier(
                network=self._inputs.network,
                generators=self._inputs.dynamic_generators,
                cc_identifier_type=self._identifier_type,
                threshold=self._threshold,
                min_cluster_power=min_cluster_power,
                threshold_decrement=self._threshold_decrement,
                critical_generator_names=self._critical_generator_names,
                maximum_number_candidates=self._max_number_candidates,
                observation_moment_id=self._observation_moment_id,
                during_fault_identification_time_step=self._during_fault_identification_time_step,
                during_fault_identification_plot_times=self._during_fault_identification_plot_times,
                significant_angle_variation_threshold=self._significant_angle_variation_threshold,
                try_all_combinations=self._try_all_combinations,
                tso_customization=self._tso_customization,
                never_critical_generators=self._never_critical_generators
            )

            # Generate outputs; paying attention to perform a copy for future uses
            candidates, self._candidate_clusters = tee(critical_cluster_identifier.candidate_clusters)

            if self._identifier_type == DuringFaultTrajectoryCriticalClustersIdentifier:
                self._max_angle_at_dft_identification_time = critical_cluster_identifier._max_angle_at_dft_identification_time

                if self._significant_angle_variation_threshold is not None:
                    angle_variation_is_negligible = self._max_angle_at_dft_identification_time <= self._significant_angle_variation_threshold
                    if angle_variation_is_negligible:
                        self._candidate_clusters = [self._candidate_clusters[0]]

            self._outputs = CriticalClustersIdentifierNodeOutputs(clusters_iterator=candidates)

    def _generate_report(self) -> str:
        """
        Generate an output report as a string.
        """
        # Get initial report
        report = super()._generate_report()

        # Configuration
        cluster_power_str = self._min_cluster_power if self._min_cluster_power is not None else "None"
        report = (
            f"{report}\tConfiguration:\n"
            f"\t\tType of identifier: {self._identifier_type.__name__}\n"
            f"\t\tThreshold: {self._threshold}\n"
            f"\t\tMinimum cluster power: {cluster_power_str}\n"
            f"\t\tThreshold decrement: {self._threshold_decrement}\n"
            f"\t\tMaximum number of candidates: {self._max_number_candidates}\n"
        )
        if self._never_critical_generators:
            report = f"{report}\t\tNever critical generators: {', '.join(self._never_critical_generators)}\n"
        if self._identifier_type == ConstrainedCriticalClustersIdentifier:
            critical_generators = ", ".join(self._critical_generator_names)
            report = f"{report}\t\tCritical generator names: {critical_generators}\n"
        elif self._identifier_type == TrajectoryCriticalClustersIdentifier:
            report = f"{report}\t\tObservation moment ID: {self._observation_moment_id}\n"
        elif self._identifier_type == DuringFaultTrajectoryCriticalClustersIdentifier:
            report = f"{report}\t\tduring fault identification time step: {self._during_fault_identification_time_step}\n"
            if self._significant_angle_variation_threshold is not None:
                report = f"{report}\t\tsignificant angle variation threshold: {self._significant_angle_variation_threshold}\n"

        # Inputs
        if self._inputs is not None:
            dynamic_generators = ", ".join(sorted(gen.name for gen in self._inputs.dynamic_generators))
            report = (
                f"{report}\tInputs:\n"
                f"\t\tGenerators: {dynamic_generators}\n"
            )

        # Outputs
        if self.cancelled or self.failed:
            # No output
            return report
        report = f"{report}\tOutputs:\n\t\tCritical cluster candidates:\n"
        for cluster_nb, (critical_cluster, _) in enumerate(self._candidate_clusters):
            generators = ", ".join(sorted(gen.name for gen in critical_cluster.generators))
            report = f"{report}\t\t\tCluster {cluster_nb}: {generators}\n"
        if self._identifier_type == DuringFaultTrajectoryCriticalClustersIdentifier:
            report = f"{report}\t\tmax_angle_at_dft_identification_time: \
            {round(self._max_angle_at_dft_identification_time, 3)}\n"
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
        EEACTreeNode.validate_configuration(node_data, node_dtos.CriticalClustersIdentifierConfiguration)
        configuration = node_data.configuration

        # Convert critical clusters identifier type
        cc_identifier_type = CCIdentifiers[configuration.identifier_type]

        # Get minimum power for cluster candidates
        min_cluster_power = None
        if configuration.min_cluster_power is not None:
            power_search = POWER_PATTERN.search(configuration.min_cluster_power)
            power, unit = power_search.groups()
            min_cluster_power = Value(float(power), Unit(unit))

        # Create instance
        return CriticalClustersIdentifierNode(
            id=node_data.id,
            name=node_data.name,
            identifier_type=cc_identifier_type,
            threshold=configuration.threshold,
            min_cluster_power=min_cluster_power,
            threshold_decrement=configuration.threshold_decrement,
            max_number_candidates=configuration.max_number_candidates,
            critical_generator_names=configuration.critical_generator_names,
            observation_moment_id=configuration.observation_moment_id,
            must_display_report=configuration.display_report,
            during_fault_identification_time_step=configuration.during_fault_identification_time_step,
            during_fault_identification_plot_times=configuration.during_fault_identification_plot_times,
            significant_angle_variation_threshold=configuration.significant_angle_variation_threshold,
            try_all_combinations=configuration.try_all_combinations,
            tso_customization=configuration.tso_customization,
            never_critical_generators=configuration.never_critical_generators
        )
