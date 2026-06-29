"""
Module for eeac.

:module: eeac
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import os
import re
from typing import List, Optional, Sequence, Set, Tuple, Union

import numpy as np

from deeac.Models.constants import BASE_POWER
from deeac.Models.generator_snapshot import GeneratorSnapshot
from deeac.Models.generator_cluster import GeneratorCluster
from deeac.Models.network import Network, NetworkComputed
from deeac.Simulations.OMIB.omib import OMIBStabilityState
from deeac.Simulations.OMIB.zoomib import ZOOMIB
from deeac.Simulations.RotorAngleTrajectoryCalculator.omib_series import OMIBTaylorSeries
from deeac.Simulations.eac import EAC
from deeac.Simulations.min_selector import select_min_critical_cluster
from deeac.Simulations.selector import CriticalClusterResults
from deeac.Simulations.identifiers.critical_clusters_identifier import (
    CriticalClustersIdentifierFactory,
)
from deeac.Simulations.identifiers.during_fault_trajectory_identifier import (
    DuringFaultTrajectoryCriticalClustersIdentifier,
)
from deeac.IO.inputs import EEACInputs
from deeac.IO.plan_models import (
    EvaluationNode,
    EvaluatorConfig,
    ExecutionPlan,
    IdentifierConfig,
    SelectorConfig,
)
from deeac.Simulations.results import EEACResult


class EEAC:
    """
    Eeac.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar execution_tree: linear EEAC execution plan (identifier -> evaluator -> selector).
    :ivar network: network for which the OMIB equivalent is built.
    :ivar output_dir: output directory for optional artifacts.
    :ivar warn: if True, failures in candidate evaluation surface as a global warning.
    """

    def __init__(
        self,
        execution_tree: ExecutionPlan,
        network: Network,
        output_dir: Optional[str] = None,
        warn: bool = False,
    ):
        """
        Initialize the EAC service.
        
        :param execution_tree: Linear execution plan.
        :param network: Network to which EEAC must be applied.
        :param output_dir: Path to an output directory, if node results must be outputted in files.
        :param warn: warning if there's a failing critical cluster candidate
        """
        self._execution_plan = execution_tree
        self._network = network
        self._output_dir = output_dir
        self._inputs: Optional[EEACInputs] = None
        self._warn = warn
        self.critical_result = None

    def provide_inputs(self, inputs: EEACInputs) -> None:
        """
        Provide the inputs to the EEAC service.
        
        :param inputs: Inputs to provide to the service.
        :return: Return value.
        """
        if inputs.output_dir is not None:
            self._output_dir = inputs.output_dir
        if self._output_dir is not None:
            os.makedirs(self._output_dir, exist_ok=True)
        inputs.output_dir = self._output_dir
        inputs.network = self._network
        self._inputs = inputs

    def run(self) -> str:
        """
        Run the EEAC pipeline for the provided inputs.
        
        The pipeline follows the paper's concept:
        1) Identify critical/non-critical generator clusters (CC/NC).
        2) Build an OMIB equivalent and apply EAC to get CCA/CCT.
        3) Select the most critical candidate.
        
        :return: Return value.
        :rtype: str
        """
        if self._inputs is None:
            raise ValueError("EEAC inputs were not provided.")

        context = self._inputs
        clusters: Optional[List[Tuple[GeneratorCluster, GeneratorCluster]]] = None
        cluster_results: Optional[List[CriticalClusterResults]] = None
        warning_message: Optional[str] = None

        for node in self._execution_plan:
            node_type = node.node_type
            if node_type == "CriticalClustersIdentifier":
                if node.identifier_config is None:
                    raise ValueError("Missing identifier configuration.")
                clusters = _run_critical_clusters_identifier(
                    node.identifier_config,
                    context.network,
                    context.computed,
                    context.generator_snapshot,
                )
            elif node_type == "CriticalClustersEvaluator":
                if node.evaluator_config is None:
                    raise ValueError("Missing evaluator configuration.")
                cluster_results, failed_clusters = _run_critical_clusters_evaluator(
                    node.evaluator_config,
                    context.network,
                    context.computed,
                    clusters,
                )
                if failed_clusters:
                    failures = [str(i) for i in sorted(failed_clusters)]
                    warning_message = f"{len(failures)} failed candidates: {', '.join(failures)}"
            elif node_type == "CriticalClusterSelector":
                if node.selector_config is None:
                    raise ValueError("Missing selector configuration.")
                selected = _run_critical_cluster_selector(
                    node_id=node.node_id,
                    config=node.selector_config,
                    cluster_results=cluster_results,
                )
                if warning_message and self._warn:
                    self.critical_result = EEACResult(
                        status="COMPUTATION_FAILURE",
                        failure_report=f"{warning_message}. Failure is global because of --warn option."
                    )
                else:
                    self.critical_result = selected
                    if warning_message:
                        self.critical_result.warning = warning_message
            else:
                raise ValueError(f"Unsupported node type in execution plan: {node_type}")

        return ""

    def reset(self):
        """
        Reset.
        
        :return: Return value.
        """
        self._inputs = None
        self.critical_result = None


POWER_PATTERN = re.compile(r"^(\d*\.{0,1}\d+)\s*(MW|kW|W)$")


def _run_critical_clusters_identifier(
    config: IdentifierConfig,
    network: Network,
    computed: NetworkComputed,
    generator_snapshot: GeneratorSnapshot,
) -> List[Tuple[GeneratorCluster, GeneratorCluster]]:
    """
    Identify critical/non-critical generator clusters.
    
    The EEAC paper assumes loss of synchronism starts with a split into a critical group
    and a non-critical group. This function produces candidate splits based on the
    configured identifier.
    :param config: Identifier configuration.
    :param network: network.
    :param computed: computed network cache.
    :param generator_snapshot: generator snapshot.
    """
    identifier_type = config.identifier_type
    if identifier_type != "DFT":
        raise ValueError(f"Unsupported identifier_type: {identifier_type}")

    min_cluster_power = None
    if config.min_cluster_power is not None:
        power_search = POWER_PATTERN.search(str(config.min_cluster_power))
        if power_search:
            power, _ = power_search.groups()
            min_cluster_power = float(power) / BASE_POWER

    tso_customization = config.tso_customization
    if tso_customization == "RTE":
        candidates: List[Tuple[GeneratorCluster, GeneratorCluster]] = []
        no_hydro_identifier: DuringFaultTrajectoryCriticalClustersIdentifier = _build_identifier_from_config(
            network, computed, generator_snapshot, config, min_cluster_power, "NO_HYDRO"
        )
        candidates.extend(list(no_hydro_identifier.candidate_clusters))
        nuclear_identifier: DuringFaultTrajectoryCriticalClustersIdentifier = _build_identifier_from_config(
            network, computed, generator_snapshot, config, min_cluster_power, "NUCLEAR"
        )
        candidates.extend(list(nuclear_identifier.candidate_clusters))

        unique_candidates = list()
        unique_generators = list()
        for candidate in candidates:
            names = {gen.name for gen in candidate[0].generators}
            if names in unique_generators:
                continue
            unique_candidates.append(candidate)
            unique_generators.append(names)

        # Preserve the original identifier order when two candidates have the same
        # size. This keeps warning indices deterministic across NumPy versions.
        order = np.argsort([len(gen_set) for gen_set in unique_generators], kind="stable")
        candidates = [unique_candidates[i] for i in order]
        max_candidates = config.max_number_candidates
        if 0 < max_candidates < len(candidates):
            candidates = candidates[:max_candidates]
        threshold = config.significant_angle_variation_threshold
        if threshold is not None:
            max_angle = no_hydro_identifier.max_angle_at_identification_time()
            if max_angle <= threshold:
                candidates = candidates[:1]
        return candidates

    identifier: DuringFaultTrajectoryCriticalClustersIdentifier = _build_identifier_from_config(
        network, computed, generator_snapshot, config, min_cluster_power, tso_customization
    )
    candidates = list(identifier.candidate_clusters)
    threshold = config.significant_angle_variation_threshold
    if threshold is not None:
        max_angle = identifier.max_angle_at_identification_time()
        if max_angle <= threshold:
            candidates = candidates[:1]
    return candidates


def _build_identifier_from_config(
    network: Network,
    computed: NetworkComputed,
    generator_snapshot: GeneratorSnapshot,
    config: IdentifierConfig,
    min_cluster_power: Optional[float],
    tso_customization: str,
) -> DuringFaultTrajectoryCriticalClustersIdentifier:
    """
    build identifier from config.
    :param network: network.
    :param computed: computed network cache.
    :param generator_snapshot: generator snapshot.
    :param config: identifier configuration.
    :param min_cluster_power: min cluster power.
    :param tso_customization: tso customization.
    """
    return CriticalClustersIdentifierFactory.get_identifier(
        network=network,
        computed=computed,
        generator_snapshot=generator_snapshot,
        cc_identifier_type=DuringFaultTrajectoryCriticalClustersIdentifier,
        threshold=config.threshold,
        min_cluster_power=min_cluster_power,
        threshold_decrement=config.threshold_decrement,
        critical_generator_names=config.critical_generator_names,
        maximum_number_candidates=config.max_number_candidates,
        observation_moment_id=config.observation_moment_id,
        during_fault_identification_time_step=config.during_fault_identification_time_step,
        during_fault_identification_plot_times=config.during_fault_identification_plot_times,
        significant_angle_variation_threshold=config.significant_angle_variation_threshold,
        try_all_combinations=config.try_all_combinations,
        tso_customization=tso_customization,
        never_critical_generators=config.never_critical_generators,
    )


def _run_critical_clusters_evaluator(
    config: EvaluatorConfig,
    network: Network,
    computed: "NetworkComputed",
    clusters: List[Tuple[GeneratorCluster, GeneratorCluster]],
) -> Tuple[List[CriticalClusterResults], Set[int]]:
    """
    run critical clusters evaluator.
    
    :param config: evaluator configuration.
    :param network: network.
    :param computed: computed network cache.
    :param clusters: clusters.
    """
    if clusters is None:
        raise ValueError("Critical clusters were not identified.")

    sequence_nodes = config.evaluation_sequence.nodes
    cluster_results: List[CriticalClusterResults] = []
    failed_clusters: Set[int] = set()
    first_exception: Optional[Exception] = None

    for cluster_nb, (critical_cluster, non_critical_cluster) in enumerate(clusters):
        try:
            results = _run_evaluation_sequence(
                sequence_nodes,
                network,
                computed,
                critical_cluster,
                non_critical_cluster,
            )
            cluster_results.append(results)
        except Exception as exc:
            failed_clusters.add(cluster_nb)
            if first_exception is None:
                first_exception = exc

    if not cluster_results:
        if first_exception is None:
            raise ValueError("No critical cluster results were produced.")
        raise ValueError(f"No critical cluster results were produced. Last error: {first_exception!r}")

    return cluster_results, failed_clusters


def _run_evaluation_sequence(
    sequence_nodes: Sequence[EvaluationNode],
    network: Network,
    computed: "NetworkComputed",
    critical_cluster: GeneratorCluster,
    non_critical_cluster: GeneratorCluster,
) -> CriticalClusterResults:
    """
    run evaluation sequence.
    
    :param sequence_nodes: sequence nodes.
    :param network: network.
    :param computed: computed network cache.
    :param critical_cluster: critical cluster.
    :param non_critical_cluster: non critical cluster.
    """
    omib = None
    critical_angle = None
    maximum_angle = None

    for node in sequence_nodes:
        node_type = node.node_type

        if node_type == "OMIB":
            omib_config = node.omib_config
            if omib_config is None:
                raise ValueError("OMIB configuration is missing.")
            omib_type = omib_config.omib_type
            if omib_type != "ZOOMIB":
                raise ValueError(f"Unsupported OMIB type: {omib_type}")
            omib = ZOOMIB(
                network=network,
                computed=computed,
                critical_cluster=critical_cluster,
                non_critical_cluster=non_critical_cluster,
            )

        elif node_type == "EAC":
            if omib is None:
                raise ValueError("EAC requires OMIB results.")
            eac_config = node.eac_config
            if eac_config is None:
                raise ValueError("EAC configuration is missing.")
            angle_increment = np.deg2rad(eac_config.angle_increment)
            max_integration_angle = np.deg2rad(eac_config.max_integration_angle)
            eac = EAC(omib, angle_increment, max_integration_angle)
            critical_angle = eac.critical_clearing_angle
            maximum_angle = eac.maximum_angle

        elif node_type == "OMIBTrajectoryCalculator":
            if omib is None or critical_angle is None or maximum_angle is None:
                raise ValueError("OMIB trajectory calculation requires OMIB and EAC results.")
            trajectory_config = node.trajectory_config
            if trajectory_config is None:
                raise ValueError("Trajectory configuration is missing.")
            calculator_type = trajectory_config.calculator_type
            if calculator_type != "TAYL":
                raise ValueError(f"Unsupported OMIB calculator type: {calculator_type}")
            critical_angle_shift = np.deg2rad(trajectory_config.critical_angle_shift)
            calculator = OMIBTaylorSeries(omib, critical_angle_shift)

            if omib.stability_state == OMIBStabilityState.ALWAYS_STABLE:
                critical_time, maximum_time = np.inf, np.inf
            else:
                critical_time, maximum_time = calculator.get_trajectory_times(
                    angles=[critical_angle, maximum_angle],
                    transition_angle=critical_angle,
                )

            if critical_time > 1:
                critical_time, maximum_time = np.inf, np.inf
                omib.stability_state = OMIBStabilityState.ALWAYS_STABLE

            generators = omib.critical_cluster.generators + omib.non_critical_cluster.generators
            return CriticalClusterResults(
                critical_cluster=omib.critical_cluster,
                non_critical_cluster=omib.non_critical_cluster,
                critical_angle=critical_angle,
                critical_time=critical_time,
                maximum_angle=maximum_angle,
                maximum_time=maximum_time,
                generators=generators,
                omib_stability_state=omib.stability_state,
                omib_swing_state=omib.swing_state,
            )
        else:
            raise ValueError(f"Unsupported evaluation node type: {node_type}")

    raise ValueError("Evaluation sequence did not produce cluster results.")


def _run_critical_cluster_selector(
    node_id: Union[str, int, None],
    config: SelectorConfig,
    cluster_results: List[CriticalClusterResults],
) -> EEACResult:
    """
    run critical cluster selector.
    
    :param node_id: node id.
    :param config: selector configuration.
    :param cluster_results: cluster results.
    """
    if not cluster_results:
        raise ValueError("No cluster results to select from.")

    selector_type = config.selector_type
    if selector_type != "MIN":
        raise ValueError(f"Unsupported selector type: {selector_type}")

    cluster_id = select_min_critical_cluster(cluster_results)
    results = cluster_results[cluster_id]
    generators = ", ".join(sorted(gen.name for gen in results.critical_cluster.generators))
    cct = None
    if results.omib_stability_state == OMIBStabilityState.POTENTIALLY_STABLE:
        cct = results.critical_time
    return EEACResult(
        status=str(results.omib_stability_state.value),
        swing_state=results.omib_swing_state.value,
        critical_cluster=generators,
        node_id=node_id,
        cct=cct,
    )
