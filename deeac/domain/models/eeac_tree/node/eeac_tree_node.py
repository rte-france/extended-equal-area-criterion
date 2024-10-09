# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Set, Union, Type
from enum import Enum
from abc import ABC, abstractmethod
from pydantic import BaseModel
from importlib import import_module
from datetime import datetime

from deeac.domain.exceptions import (
    DEEACExceptionCollector, DEEACExceptionList, EEACTreeNodeOutputsException, EEACTreeNodeTypeException,
    EEACNodeConfigurationException, EEACTreeNodeInputsException, EEACTreeNodeCancelledException
)
import deeac.domain.ports.dtos.eeac_tree as node_dtos
from deeac.domain.models.generator_cluster import GeneratorCluster
from deeac.domain.models import DynamicGenerator
from deeac.domain.models.omib import OMIBStabilityState, OMIBSwingState


class EEACTreeNodeIOType(Enum):
    """
    Type of an input or output of a tree node.
    The values correspond to the keys in EEACTreeNodeIOs.
    Configuration variables are not included.
    """
    NETWORK = "network"
    DYNAMIC_GENERATORS = "dynamic_generators"
    CRIT_CLUSTER = "critical_cluster"
    NON_CRIT_CLUSTER = "non_critical_cluster"
    CLUSTERS_ITERATOR = "clusters_iterator"
    CRIT_ANGLE = "critical_angle"
    CRIT_TIME = "critical_time"
    MAX_ANGLE = "maximum_angle"
    MAX_TIME = "maximum_time"
    OMIB = "omib"
    OMIB_STABILIY_STATE = "omib_stability_state"
    OMIB_SWING_STATE = "omib_swing_state"
    CLUSTER_RESULTS = "cluster_results"
    CLUSTER_RESULTS_ITERATOR = "cluster_results_iterator"
    OUTPUT_DIR = "output_dir"


class EEACTreeNodeIOs(BaseModel, ABC):
    """
    Base class of node inputs and outputs
    """
    class Config:
        arbitrary_types_allowed = True


class EEACClusterResults(EEACTreeNodeIOs):
    """
    Results of EEAC on a specific critical cluster
    """
    critical_angle: float
    critical_time: float
    maximum_angle: float
    maximum_time: float
    critical_cluster: GeneratorCluster
    non_critical_cluster: GeneratorCluster
    omib_stability_state: OMIBStabilityState
    omib_swing_state: OMIBSwingState
    dynamic_generators: Set[DynamicGenerator]


class EEACTreeNode(ABC):
    """
    Node of and EEAC execution tree.
    """

    def __init__(self, id: Union[str, int], name: str = None, must_display_report: bool = False):
        """
        Initialize the tree node

        :param id: Unique identifier of the node.
        :param name: Name of the node.
        :param must_display_report: True if a report must be outputted for the node.
        """
        self._id = id
        self._name = name

        self._exceptions = None
        self._input_types = None
        self._output_types = None
        self._inputs = None
        self._outputs = None
        self._cancelled = False
        self._cancel_msg = None
        self._failed = False
        self._execution_time = 0

        # Output directory to use for reports if no input provided
        self._output_dir = None

        # Define if a report or graph must be outputted
        self.must_display_report = must_display_report

    def _verify_inputs(self):
        """
        Check that inputs were provided.
        :raise EEACTreeNodeInputsException if the inputs are not valid.
        """
        try:
            assert self._inputs is not None
        except AssertionError:
            raise EEACTreeNodeInputsException(self)

    @property
    def failed(self) -> bool:
        """
        Determine if the node is in failure mode.

        :return: True if the node encountered problems and is in failure mode.
        """
        return not self._cancelled and self._exceptions is not None

    @property
    def cancelled(self) -> bool:
        """
        Determine if the execution of this node was cancelled.
        """
        return self._cancelled

    def cancel(self, cancel_msg: str = None, log_dir: str = None):
        """
        Cancel execution of this node.

        :param cancel_msg: A message justifying why the node was cancelled.
        :param log_dir: Path to an output directory for logging.
        """
        self._cancel_msg = cancel_msg
        self._output_dir = log_dir
        self._cancelled = True

    @property
    def input_types(self) -> Set[EEACTreeNodeIOType]:
        """
        Inputs requested by this node from previous nodes.

        :return: Set of EEAC node IOs.
        """
        return self._input_types

    @property
    def output_types(self) -> Set[EEACTreeNodeIOType]:
        """
        Outputs returned by this node.

        :return: Set of EEAC node IOs.
        """
        return self._output_types

    @property
    def outputs(self) -> EEACTreeNodeIOs:
        """
        Retrieve the outputs of this node.

        :return: Output values.
        :raise EEACTreeNodeOutputsException if the node was not run.
        """
        if self._outputs is None:
            # Node was not run
            raise EEACTreeNodeOutputsException(self)
        return self._outputs

    @property
    def inputs(self) -> EEACTreeNodeIOs:
        """
        Provide the inputs to this node.

        :return: Input values.
        """
        return self._inputs

    @property
    @abstractmethod
    def expected_inputs_dto_type(self) -> Type[EEACTreeNodeIOs]:
        """
        Return the expected type of DTO for the inputs.

        :return: The type of DTO.
        """
        pass

    @inputs.setter
    @abstractmethod
    def inputs(self, inputs: EEACTreeNodeIOs):
        """
        Provide the inputs to this node.

        :param inputs: Input values.
        :raise EEACTreeNodeInputsException if the input is not expected by this node.
        """
        pass

    @property
    def name(self) -> str:
        """
        Return the node name.
        """
        return self._name

    @property
    def id(self) -> Union[str, int]:
        """
        Return the node ID.
        """
        return self._id

    @property
    def complete_id(self) -> str:
        """
        Complete identifier of the node, consisting in the concatenation of its ID and its name, if it exits, otherwise
        the ID alone.
        """
        if self._name is not None:
            return f"{self._id}_{self._name}"
        return self._id

    @abstractmethod
    def can_be_leaf(self) -> bool:
        """
        Determine if the node can be a leaf in the tree.

        :return: True if the node can be a leaf, False otherwise.
        """
        pass

    def run(self):
        """
        Run the node in order to produce the output values.
        """
        # Reset bools
        self._failed = False
        self._exceptions = None
        self._outputs = None

        exception_collector = DEEACExceptionCollector()
        with exception_collector:
            if self.cancelled:
                # Node execution was cancelled
                raise EEACTreeNodeCancelledException(self)
            if self._inputs is None:
                # No input provided
                self._failed = True
                raise EEACTreeNodeInputsException(self)
            start_time = datetime.now()
            self._run()
            self._execution_time = (datetime.now() - start_time).total_seconds()

        # Keep exceptions, if any
        try:
            exception_collector.raise_for_exception()
        except DEEACExceptionList as exceptions:
            self._failed = True
            self._exceptions = exceptions
        return self._finalize()

    @abstractmethod
    def _run(self):
        """
        Run the node in order to produce the output values.

        :raise: A DEEACExceptionList in case of errors.
        """
        pass

    @abstractmethod
    def _generate_report(self) -> str:
        """
        Generate an output report as a string.
        """
        report = f"Report for node {self.complete_id}:\n"
        if self.cancelled:
            if self._cancel_msg is not None:
                return f"{report}\tExecution was cancelled: {self._cancel_msg}\n"
            return f"{report}\tExecution was cancelled.\n"
        elif self.failed:
            # Errors were observed
            errors_description = str(self._exceptions)
            return f"{report}\tExecution failed due to the following errors: {errors_description}\n"
        if self._execution_time != 0:
            return f"{report}\tExecution time: {round(self._execution_time, 3)} seconds\n"
        return report

    def _finalize(self) -> str:
        """
        Method run after execution of the node.
        Output errors if any, and write results if asked.
        """
        # Generate report
        report = self._generate_report()

        # Open output file, if any
        output_dir = self._inputs.output_dir if self._inputs is not None else None
        if output_dir is None:
            # Check if output directory was provided manually
            output_dir = self._output_dir
        output_file = open(f"{output_dir}/{self.complete_id}.txt", "w") if output_dir is not None else None
        if output_file is not None:
            output_file.write(f"{report}\n\n")
        #if self.must_display_report or self.failed:
        #    print(f"{report}\n")

        if output_file is not None:
            # Close file
            output_file.close()
        return report

    @classmethod
    @abstractmethod
    def create_node(cls, node_data: node_dtos.EEACTreeNode) -> 'EEACTreeNode':
        """
        Create an EEAC tree node based on DTO values.

        :param node_data: Node data to use for creation.
        :return: The EEAC tree node.
        :raise EEACTreeNodeTypeException: If the type of node is not recognized.
        :raise EEACNodeConfigurationException if the node configuration is not valid.
        """
        try:
            # Create node
            module = import_module("deeac.domain.models.eeac_tree.node")
            node_class = getattr(module, f"{node_data.type.value}Node")
        except AttributeError:
            raise EEACTreeNodeTypeException(node_data.id, node_data.name, node_data.type.value)
        return node_class.create_node(node_data)

    @classmethod
    def validate_configuration(
        cls, node_data: node_dtos.EEACTreeNode, expected_type: Type[node_dtos.EEACNodeConfiguration]
    ):
        """
        Validate if a node configuration is existing and of the right type.

        :param node_data: Node data containing its configuration.
        :param expected_type: Expected configuration type.
        :raise EEACNodeConfigurationException if the configuration is invalid.
        """
        config_type = type(node_data.configuration)
        if config_type != expected_type:
            # Invalid configuration
            raise EEACNodeConfigurationException(
                node_id=node_data.id,
                node_name=node_data.name,
                configuration_type=config_type.__name__,
                node_type=expected_type.__name__
            )

    def reset(self):
        """
        Reset the node, deleting the inputs, outputs and state.
        """
        self._exceptions = None
        self._inputs = None
        self._outputs = None
        self._cancelled = False
        self._cancel_msg = None
        self._execution_time = 0
