"""
Module for plan_loader.

:module: plan_loader
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.
"""

from __future__ import annotations
import json
from json.decoder import JSONDecodeError
from typing import Dict, List, Optional

from deeac.IO.plan_models import (
    EACConfig,
    EvaluationNode,
    EvaluationSequence,
    EvaluatorConfig,
    ExecutionNode,
    ExecutionPlan,
    IdentifierConfig,
    OMIBConfig,
    OMIBTrajectoryConfig,
    SelectorConfig,
)


def _as_list(value: str | int | float) -> Optional[List[str | int | float]]:
    """
    Normalize an optional value into a list.
    
    :param value: Input value.
    :return: List value or None.
    """
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return None


def _follow_single_branch(root_node: Dict[str, str | int | float]) -> List[Dict[str, str | int | float]]:
    """
    Follow the single branch of a tree plan.
    
    :param root_node: Root node payload.
    :return: Linear list of nodes.
    """
    nodes: List[Dict[str, str | int | float]] = []
    node = root_node
    while node is not None:
        nodes.append(node)
        children = node.get("children") or []
        if len(children) > 1:
            raise ValueError("Execution plan must be a single linear branch, not a tree.")
        node = children[0] if children else None
    return nodes


def _parse_evaluation_node(node_data: Dict[str, str | int | float]) -> EvaluationNode:
    """
    Parse a single evaluation node from raw data.
    
    :param node_data: Node payload.
    :return: Parsed evaluation node.
    """
    node_type = node_data.get("type")
    if not isinstance(node_type, str):
        raise ValueError("Evaluation node type must be a string.")
    config = node_data.get("configuration") or {}
    if not isinstance(config, dict):
        raise ValueError("Evaluation node configuration must be an object.")

    if node_type == "OMIB":
        omib_type = config.get("omib_type")
        return EvaluationNode(node_type=node_type, omib_config=OMIBConfig(omib_type=omib_type))
    if node_type == "EAC":
        angle_increment = float(config.get("angle_increment", 0.1))
        max_integration_angle = float(config.get("max_integration_angle", 360))
        return EvaluationNode(
            node_type=node_type,
            eac_config=EACConfig(angle_increment=angle_increment, max_integration_angle=max_integration_angle),
        )
    if node_type == "OMIBTrajectoryCalculator":
        calculator_type = config.get("calculator_type")
        critical_angle_shift = float(config.get("critical_angle_shift", 0.0))
        return EvaluationNode(
            node_type=node_type,
            trajectory_config=OMIBTrajectoryConfig(
                calculator_type=calculator_type,
                critical_angle_shift=critical_angle_shift,
            ),
        )
    raise ValueError(f"Unsupported evaluation node type: {node_type}")


def _parse_evaluation_sequence(data: Dict[str, str | int | float]) -> EvaluationSequence:
    """
    Parse an evaluation sequence from raw data.
    
    :param data: Sequence payload.
    :return: Parsed evaluation sequence.
    """
    nodes_data = data.get("nodes") or []
    if not isinstance(nodes_data, list):
        raise ValueError("Evaluation sequence nodes must be a list.")
    nodes = [_parse_evaluation_node(node) for node in nodes_data]
    return EvaluationSequence(nodes=nodes)


def _parse_identifier_config(config: Dict[str, str | int | float]) -> IdentifierConfig:
    """
    Parse the identifier configuration.
    
    :param config: Configuration payload.
    :return: Identifier configuration.
    """
    return IdentifierConfig(
        identifier_type=config.get("identifier_type"),
        during_fault_identification_time_step=float(config.get("during_fault_identification_time_step", 0.0)),
        significant_angle_variation_threshold=(
            float(config["significant_angle_variation_threshold"])
            if config.get("significant_angle_variation_threshold") is not None
            else None
        ),
        min_cluster_power=config.get("min_cluster_power"),
        tso_customization=str(config.get("tso_customization", "default")),
        max_number_candidates=int(config.get("max_number_candidates", 0)),
        never_critical_generators=_as_list(config.get("never_critical_generators")),
        threshold=float(config["threshold"]) if config.get("threshold") is not None else None,
        threshold_decrement=float(config.get("threshold_decrement", 0.1)),
        critical_generator_names=_as_list(config.get("critical_generator_names")),
        observation_moment_id=int(config.get("observation_moment_id", -1)),
        during_fault_identification_plot_times=_as_list(config.get("during_fault_identification_plot_times")),
        try_all_combinations=bool(config.get("try_all_combinations", False)),
    )


def _parse_evaluator_config(config: Dict[str, str | int | float]) -> EvaluatorConfig:
    """
    Parse the evaluator configuration.
    
    :param config: Configuration payload.
    :return: Evaluator configuration.
    """
    sequence_data = config.get("evaluation_sequence") or {}
    if not isinstance(sequence_data, dict):
        raise ValueError("Evaluation sequence configuration must be an object.")
    return EvaluatorConfig(evaluation_sequence=_parse_evaluation_sequence(sequence_data))


def _parse_selector_config(config: Dict[str, str | int | float]) -> SelectorConfig:
    """
    Parse the selector configuration.
    
    :param config: Configuration payload.
    :return: Selector configuration.
    """
    return SelectorConfig(selector_type=config.get("selector_type"))


def _parse_execution_node(node_data: Dict[str, str | int | float]) -> ExecutionNode:
    """
    Parse a single execution node from raw data.
    
    :param node_data: Node payload.
    :return: Parsed execution node.
    """
    node_type = node_data.get("type")
    if not isinstance(node_type, str):
        raise ValueError("Execution node type must be a string.")
    config = node_data.get("configuration") or {}
    if not isinstance(config, dict):
        raise ValueError("Execution node configuration must be an object.")

    identifier_config = None
    evaluator_config = None
    selector_config = None

    if node_type == "CriticalClustersIdentifier":
        identifier_config = _parse_identifier_config(config)
    elif node_type == "CriticalClustersEvaluator":
        evaluator_config = _parse_evaluator_config(config)
    elif node_type == "CriticalClusterSelector":
        selector_config = _parse_selector_config(config)
    else:
        raise ValueError(f"Unsupported node type in execution plan: {node_type}")

    return ExecutionNode(
        node_type=node_type,
        node_id=node_data.get("id"),
        name=node_data.get("name"),
        identifier_config=identifier_config,
        evaluator_config=evaluator_config,
        selector_config=selector_config,
    )


def parse_execution_plan_data(data: Dict[str, str | int | float]) -> ExecutionPlan:
    """
    Parse raw execution plan data into an ExecutionPlan.
    
    :param data: Raw plan payload.
    :return: Parsed execution plan.
    """
    if "branch" in data:
        branch_data = data["branch"]
        if isinstance(branch_data, dict):
            data = branch_data
        else:
            raise ValueError("Execution plan branch must be an object.")

    if "root" in data:
        root = data["root"]
        if not isinstance(root, dict):
            raise ValueError("Execution plan root must be an object.")
        nodes_data = _follow_single_branch(root)
    elif "nodes" in data:
        nodes_data = data["nodes"]
        if not isinstance(nodes_data, list):
            raise ValueError("Execution plan nodes must be a list.")
    else:
        raise ValueError("Execution plan must define a root or a nodes list.")

    nodes = [_parse_execution_node(node) for node in nodes_data]
    return ExecutionPlan(nodes=nodes)


def read_execution_plan(
    execution_tree_file: Optional[str],
    execution_tree: Optional[ExecutionPlan],
) -> ExecutionPlan:
    """
    Read execution plan from a file or in-memory object.
    
    :param execution_tree_file: Path to the execution plan file.
    :param execution_tree: Parsed execution plan.
    :return: Parsed execution plan.
    """
    if execution_tree is not None:
        return execution_tree
    if execution_tree_file is None:
        raise ValueError("Execution plan not provided.")
    try:
        data = json.load(open(execution_tree_file))
    except JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON execution plan: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("Execution plan JSON must be an object.")
    return parse_execution_plan_data(data)
