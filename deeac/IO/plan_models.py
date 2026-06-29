"""
Execution plan models.

:module: plan_models
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List, Optional, Sequence, Union


class OMIBConfig:
    """
    OMIB node configuration.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar omib_type: OMIB model type identifier.
    """

    def __init__(self, omib_type: Optional[str]) -> None:
        """
        Initialize the OMIB configuration.
        
        :param omib_type: OMIB model type identifier.
        :return: Return value.
        """
        self.omib_type = omib_type


class EACConfig:
    """
    EAC node configuration.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar angle_increment: Angle increment in degrees.
    :ivar max_integration_angle: Maximum integration angle in degrees.
    """

    def __init__(self, angle_increment: float, max_integration_angle: float) -> None:
        """
        Initialize the EAC configuration.
        
        :param angle_increment: Angle increment in degrees.
        :param max_integration_angle: Maximum integration angle in degrees.
        :return: Return value.
        """
        self.angle_increment = angle_increment
        self.max_integration_angle = max_integration_angle


class OMIBTrajectoryConfig:
    """
    OMIB trajectory calculator configuration.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar calculator_type: Calculator type identifier.
    :ivar critical_angle_shift: Critical angle shift in degrees.
    """

    def __init__(self, calculator_type: Optional[str], critical_angle_shift: float) -> None:
        """
        Initialize the trajectory calculator configuration.
        
        :param calculator_type: Calculator type identifier.
        :param critical_angle_shift: Critical angle shift in degrees.
        :return: Return value.
        """
        self.calculator_type = calculator_type
        self.critical_angle_shift = critical_angle_shift


class EvaluationNode:
    """
    Evaluation sequence node.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar node_type: Node type identifier.
    :ivar omib_config: OMIB node configuration.
    :ivar eac_config: EAC node configuration.
    :ivar trajectory_config: Trajectory calculator configuration.
    """

    def __init__(
        self,
        node_type: str,
        omib_config: Optional[OMIBConfig] = None,
        eac_config: Optional[EACConfig] = None,
        trajectory_config: Optional[OMIBTrajectoryConfig] = None,
    ) -> None:
        """
        Initialize the evaluation sequence node.
        
        :param node_type: Node type identifier.
        :param omib_config: OMIB node configuration.
        :param eac_config: EAC node configuration.
        :param trajectory_config: Trajectory calculator configuration.
        :return: Return value.
        """
        self.node_type = node_type
        self.omib_config = omib_config
        self.eac_config = eac_config
        self.trajectory_config = trajectory_config


class EvaluationSequence:
    """
    Evaluation sequence configuration.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar nodes: Sequence of evaluation nodes.
    """

    def __init__(self, nodes: Sequence[EvaluationNode]) -> None:
        """
        Initialize the evaluation sequence.
        
        :param nodes: Sequence of evaluation nodes.
        :return: Return value.
        """
        self.nodes = list(nodes)


class IdentifierConfig:
    """
    Critical clusters identifier configuration.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar identifier_type: Identifier type name.
    :ivar during_fault_identification_time_step: Time step during fault identification.
    :ivar significant_angle_variation_threshold: Threshold for angle variation.
    :ivar min_cluster_power: Minimum cluster power string or numeric value.
    :ivar tso_customization: TSO customization name.
    :ivar max_number_candidates: Maximum number of candidates.
    :ivar never_critical_generators: Generator names never considered critical.
    :ivar threshold: Initial identification threshold.
    :ivar threshold_decrement: Threshold decrement step.
    :ivar critical_generator_names: Generator names always considered critical.
    :ivar observation_moment_id: Observation moment index.
    :ivar during_fault_identification_plot_times: Plot times during fault identification.
    :ivar try_all_combinations: Whether to try all combinations.
    """

    def __init__(
        self,
        identifier_type: Optional[str],
        during_fault_identification_time_step: float = 0.0,
        significant_angle_variation_threshold: Optional[float] = None,
        min_cluster_power: Optional[Union[str, float]] = None,
        tso_customization: str = "default",
        max_number_candidates: int = 0,
        never_critical_generators: Optional[Sequence[str]] = None,
        threshold: Optional[float] = None,
        threshold_decrement: float = 0.1,
        critical_generator_names: Optional[Sequence[str]] = None,
        observation_moment_id: int = -1,
        during_fault_identification_plot_times: Optional[Sequence[float]] = None,
        try_all_combinations: bool = False,
    ) -> None:
        """
        Initialize the identifier configuration.
        
        :param identifier_type: Identifier type name.
        :param during_fault_identification_time_step: Time step during fault identification.
        :param significant_angle_variation_threshold: Threshold for angle variation.
        :param min_cluster_power: Minimum cluster power string or numeric value.
        :param tso_customization: TSO customization name.
        :param max_number_candidates: Maximum number of candidates.
        :param never_critical_generators: Generator names never considered critical.
        :param threshold: Initial identification threshold.
        :param threshold_decrement: Threshold decrement step.
        :param critical_generator_names: Generator names always considered critical.
        :param observation_moment_id: Observation moment index.
        :param during_fault_identification_plot_times: Plot times during fault identification.
        :param try_all_combinations: Whether to try all combinations.
        :return: Return value.
        """
        self.identifier_type = identifier_type
        self.during_fault_identification_time_step = during_fault_identification_time_step
        self.significant_angle_variation_threshold = significant_angle_variation_threshold
        self.min_cluster_power = min_cluster_power
        self.tso_customization = tso_customization
        self.max_number_candidates = max_number_candidates
        self.never_critical_generators = list(never_critical_generators) if never_critical_generators else None
        self.threshold = threshold
        self.threshold_decrement = threshold_decrement
        self.critical_generator_names = list(critical_generator_names) if critical_generator_names else None
        self.observation_moment_id = observation_moment_id
        self.during_fault_identification_plot_times = (
            list(during_fault_identification_plot_times) if during_fault_identification_plot_times else None
        )
        self.try_all_combinations = try_all_combinations


class EvaluatorConfig:
    """
    Critical clusters evaluator configuration.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar evaluation_sequence: Evaluation sequence configuration.
    """

    def __init__(self, evaluation_sequence: EvaluationSequence) -> None:
        """
        Initialize the evaluator configuration.
        
        :param evaluation_sequence: Evaluation sequence configuration.
        :return: Return value.
        """
        self.evaluation_sequence = evaluation_sequence


class SelectorConfig:
    """
    Critical cluster selector configuration.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar selector_type: Selector type identifier.
    """

    def __init__(self, selector_type: Optional[str]) -> None:
        """
        Initialize the selector configuration.
        
        :param selector_type: Selector type identifier.
        :return: Return value.
        """
        self.selector_type = selector_type


class ExecutionNode:
    """
    Execution plan node.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar node_type: Node type identifier.
    :ivar node_id: Node identifier.
    :ivar name: Node display name.
    :ivar identifier_config: Identifier configuration.
    :ivar evaluator_config: Evaluator configuration.
    :ivar selector_config: Selector configuration.
    """

    def __init__(
        self,
        node_type: str,
        node_id: Optional[Union[str, int]] = None,
        name: Optional[str] = None,
        identifier_config: Optional[IdentifierConfig] = None,
        evaluator_config: Optional[EvaluatorConfig] = None,
        selector_config: Optional[SelectorConfig] = None,
    ) -> None:
        """
        Initialize the execution plan node.
        
        :param node_type: Node type identifier.
        :param node_id: Node identifier.
        :param name: Node display name.
        :param identifier_config: Identifier configuration.
        :param evaluator_config: Evaluator configuration.
        :param selector_config: Selector configuration.
        :return: Return value.
        """
        self.node_type = node_type
        self.node_id = node_id
        self.name = name
        self.identifier_config = identifier_config
        self.evaluator_config = evaluator_config
        self.selector_config = selector_config


class ExecutionPlan:
    """
    Linear execution plan.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar nodes: Sequence of execution nodes.
    """

    def __init__(self, nodes: Sequence[ExecutionNode]) -> None:
        """
        Initialize the execution plan.
        
        :param nodes: Sequence of execution nodes.
        :return: Return value.
        """
        self.nodes: List[ExecutionNode] = list(nodes)

    def __iter__(self):
        """
        Iterate over execution nodes.
        
        :return: Iterator for execution nodes.
        :rtype: iterator
        """
        return iter(self.nodes)

    def __len__(self) -> int:
        """
        Return the number of nodes in the plan.
        
        :return: Number of nodes in the plan.
        :rtype: int
        """
        return len(self.nodes)
