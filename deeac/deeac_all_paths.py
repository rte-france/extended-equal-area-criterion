"""
Module for __main__.

:module: __main__
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List, Optional, Union, Tuple
import sys
import json
import os
import shutil
from datetime import datetime
from joblib import Parallel, delayed

try:
    from deeac.IO.dynawo.parse_dynawo import parse_dynawo_configuration
    _DYNAWO_PARSE_AVAILABLE = True
except ModuleNotFoundError:
    parse_dynawo_configuration = None
    _DYNAWO_PARSE_AVAILABLE = False
from deeac.IO.eurostag.parse_eurostag import parse_eurostag

from deeac.Simulations.eeac import EEAC
from deeac.IO.inputs import EEACInputs
from deeac.IO.plan_loader import read_execution_plan
from deeac.IO.plan_models import ExecutionPlan
from deeac.Models.generator_snapshot import GeneratorSnapshot
from deeac.Models.network import Network, NetworkComputed, NetworkState
from deeac.Models.events.fault_events import FaultEvents
from deeac.Models.events.line_short_circuit_event import LineShortCircuitEvent
from deeac.Simulations.results import EEACResults, EEACResult
from deeac.Utils.logger import Logger
from deeac.IO.arguments_parser import (
    EurostagRunConfiguration,
    DynawoRunConfiguration,
)


def apply_events_to_network(
        network: Network,
        computed: NetworkComputed,
        fault_events: FaultEvents,
) -> None:
    """
    Apply failure and mitigation events to build during-fault and post-fault networks.

    :param network: Network instance.
    :param computed: Computed network cache.
    :param fault_events: Fault events to apply.
    :return: Return value.
    """
    failure_events = fault_events.failure_events
    mitigation_events = fault_events.mitigation_events

    relevant_fault_event = False
    for fault in failure_events:
        relevant_fault_event += fault.apply_to_network(network)
    if not relevant_fault_event:
        raise IOError("Failure events happening on disconnected elements, cancelling execution")

    computed.simplified_during = network.get_simplified_network()

    for mitigation in mitigation_events:
        try:
            mitigation.apply_to_network(network)
        except IOError:
            pass
        except ValueError:
            print("Warning: opening a circuit breaker that is already open is impossible")
            pass

    computed.simplified_post = network.get_simplified_network()


def run_fault(
        execution_plan: ExecutionPlan,
        output_dir: Optional[str],
        network: Network,
        verbose: bool,
        island_threshold: float,
        fault_events: FaultEvents,
        warn: bool,
) -> Tuple[str, EEACResult, Logger]:
    """
    Runs the rest of EAC for one fault at a time.

    :param execution_plan: execution plan.
    :param output_dir: output dir.
    :param network: network instance for this fault (owned by the caller).
    :param verbose: verbose.
    :param island_threshold: island threshold.
    :param warn: warn.
    :param fault_events: Fault events entry.
    :return: Return value.
    """
    thread_starting_time = datetime.now()
    computed = NetworkComputed()
    network.initialize_simplified_network(computed)

    network_initialization_time = datetime.now()

    per_process_logger = Logger(verbose=verbose)
    per_process_logger.info(f"FAULT: {fault_events.name}")
    failure_events = fault_events.failure_events
    mitigation_events = fault_events.mitigation_events

    # Checking there is a fault in the input file
    if not failure_events or not mitigation_events:
        per_process_logger.warning("Empty fault, cancelling execution")
        return fault_events.name, EEACResult(status="Empty fault"), per_process_logger
    # Checking all protections are triggered at the same time
    if fault_events.short_circuit_delay is not None:
        per_process_logger.warning("Degraded protection case, cancelling execution")
        return fault_events.name, EEACResult(
            status="Degraded protection",
            interval=f"{fault_events.short_circuit_delay}ms"
        ), per_process_logger

    # Checking the fault is not impedant
    for failure_event in failure_events:
        if isinstance(failure_event, LineShortCircuitEvent):
            fault_resistance = failure_event.fault_resistance
            fault_reactance = failure_event.fault_reactance
            if fault_resistance != 0 or fault_reactance != 0:
                per_process_logger.warning(
                    "Faults with non-zero impedance are not yet supported, cancelling execution"
                )
                return fault_events.name, EEACResult(status="Impedant fault"), per_process_logger

    # Register time at which all files are loaded
    file_loading_time = datetime.now()
    if verbose:
        per_process_logger.info("Fault events loaded")
        for i, event in enumerate(failure_events):
            per_process_logger.info(str(event), {"index": str(i + 1)})
        per_process_logger.info("Mitigation events loaded")
        for i, event in enumerate(mitigation_events):
            per_process_logger.info(str(event), {"index": str(i + 1)})

    try:
        apply_events_to_network(network, computed, fault_events)
    except IOError as e:
        per_process_logger.error(str(e))
        return fault_events.name, EEACResult(status="Irrelevant Fault"), per_process_logger

    except Exception as e:
        per_process_logger.error(str(e))
        return fault_events.name, EEACResult(status="Error", error_msg=str(e)), per_process_logger

    # Register event processing time
    event_processing_time = datetime.now()

    disconnected_buses = dict()
    for state in NetworkState:
        try:
            disconnected_buses[state] = network.get_disconnected_buses(computed, state)
        except Exception as e:
            per_process_logger.error(str(e))
            return fault_events.name, EEACResult(status="Irrelevant Fault"), per_process_logger

    # Buses disconnected due to mitigation
    island = set(disconnected_buses[NetworkState.POST_FAULT]) - set(disconnected_buses[NetworkState.PRE_FAULT])

    # Gathering information on the island
    units = [unit for unit in network.generators if unit.bus.name in island]
    unit_names = ', '.join([unit.name for unit in units])
    production = sum(unit.active_power for unit in units)
    loads = [load for load in network.non_fictive_loads if load.bus.name in island]
    load_names = ', '.join([load.name for load in loads])
    consumption = sum(load.active_power for load in loads)

    if production > 0:

        per_process_logger.info(f"Isolated production: {production}MW - {unit_names}")

        if consumption == 0:
            per_process_logger.info("No isolated consumption")
        else:
            per_process_logger.info(f"Isolated consumption: {consumption}MW - {load_names}")

        if production > island_threshold:
            per_process_logger.warning(
                f"Islanding over threshold: {production}MW > {island_threshold}MW, cancelling execution"
            )
            return fault_events.name, EEACResult(
                status="Islanding",
                production_loss=f"{round(production, 2)}MW",
                disconnected_production=unit_names,
                consumption_loss=f"{round(consumption, 2)}MW",
                disconnected_consumption=load_names
            ), per_process_logger
        else:
            per_process_logger.info(
                f"Islanding below threshold: {production}MW <= {island_threshold}MW, carrying execution"
            )

    elif consumption > 0:
        per_process_logger.warning(f"Isolated consumption: {consumption}MW - {load_names}")

    else:
        pass

    # Check if buses are disconnected from main network component
    if network.get_disconnected_buses(computed, NetworkState.PRE_FAULT):
        per_process_logger.warning(
            "Buses are disconnected from the main network component (use -v option for details)"
        )

    # Display relevant results
    if verbose:
        per_process_logger.info("Reports")

    # Generate EEAC instance
    eeac = EEAC(execution_tree=execution_plan, network=network, output_dir=output_dir, warn=warn)

    # Provide inputs consisting in post-fault generators
    generators = network.get_state(computed, NetworkState.POST_FAULT).network.generators
    snapshot = GeneratorSnapshot(generators)
    inputs = EEACInputs(
        generator_snapshot=snapshot,
        network=network,
        computed=computed,
        output_dir=output_dir,
    )
    eeac.provide_inputs(inputs)

    # Run EEAC
    report = eeac.run()
    if verbose and report:
        per_process_logger.info(report)
    eeac_processing_time = datetime.now()

    # Get generators disconnected in each state
    generators = {}
    for state in NetworkState:
        generators[state] = {gen.name for gen in network.get_state(computed, state).network.generators}

    failure_disconnected_generators = generators[NetworkState.PRE_FAULT] - generators[NetworkState.DURING_FAULT]
    mitigation_disconnected_generators = generators[NetworkState.DURING_FAULT] - generators[NetworkState.POST_FAULT]

    if verbose and failure_disconnected_generators:
        generator_names = ", ".join(failure_disconnected_generators)
        per_process_logger.info(
            f"Generators disconnected from the main network component due to the failures: {generator_names}"
        )

    if verbose and mitigation_disconnected_generators:
        generator_names = ", ".join(mitigation_disconnected_generators)
        per_process_logger.info(
            f"Generators disconnected from the main network component due to the mitigations: {generator_names}"
        )

    # Execution times
    network_copy_time = round((network_initialization_time - thread_starting_time).total_seconds(), 3)
    event_reading_time = round((file_loading_time - network_initialization_time).total_seconds(), 3)
    event_time = round((event_processing_time - file_loading_time).total_seconds(), 3)
    tree_execution_time = round((eeac_processing_time - event_processing_time).total_seconds(), 3)
    if verbose:
        per_process_logger.info(
            "Execution times",
            {
                "fault": fault_events.name,
                "network_duplication_s": str(network_copy_time),
                "event_files_reading_s": str(event_reading_time),
                "event_processing_s": str(event_time),
                "eeac_plan_execution_s": str(tree_execution_time),
            },
        )

    if verbose and disconnected_buses[NetworkState.PRE_FAULT]:
        buses = ', '.join(disconnected_buses[NetworkState.PRE_FAULT])
        per_process_logger.info(f"Buses disconnected from the main network component: {buses}")

    return fault_events.name, eeac.critical_result, per_process_logger


def _prepare_output_dir(output_dir: Optional[str], rewrite: bool) -> None:
    """
    Prepare the output directory if requested.

    :param output_dir: Output directory path.
    :param rewrite: Whether to rewrite existing data.
    :return: Return value.
    """
    if output_dir is None:
        return
    if os.path.isdir(output_dir):
        if len(os.listdir(output_dir)) > 0:
            if not rewrite:
                user_input = input(
                    "Output directory already exists and contains data.\n"
                    "This data will be deleted. Proceed [Y/N]? "
                ).upper()
                while user_input != "Y":
                    if user_input == "N":
                        print("Data not deleted. Execution aborted.")
                        sys.exit(0)
                    else:
                        user_input = input("Please type Y for Yes or N for No: ").upper()

            shutil.rmtree(output_dir, ignore_errors=True)
            os.makedirs(output_dir)
    else:
        os.makedirs(output_dir)


def _load_network_from_config(
        config: Union[EurostagRunConfiguration, DynawoRunConfiguration],
        logger: Logger,
) -> Network:
    """
    Load the network based on the configuration type and attach fault events.

    :param config: Run configuration (Eurostag or Dynawo).
    :param logger: Logger instance.
    :return: Network instance.
    """
    if isinstance(config, EurostagRunConfiguration):
        logger.info("Loading use case")
        return parse_eurostag(
            ech_file=config.ech_file,
            dta_file=config.dta_file,
            lf_file=config.lf_file,
            seq_file=config.seq_file,
            seq_files=config.seq_files,
            protection_delay=config.protection_delay,
        )
    elif isinstance(config, DynawoRunConfiguration):
        logger.info("Loading Dynawo case")
        if _DYNAWO_PARSE_AVAILABLE:
            pass
        else:
            raise ModuleNotFoundError(
                "Dynawo workflow is optional and unavailable: missing Dynawo parser dependencies."
            )
        network = parse_dynawo_configuration(config)
        return network
    else:
        raise ValueError(f"Unsupported configuration type: {type(config)}")


def build_output_dirs(
        output_dir: Optional[str],
        fault_events: List[FaultEvents],
) -> List[Optional[str]]:
    """
    Build per-event output directories.

    :param output_dir: Base output directory.
    :param fault_events: Fault events list.
    :return: List of output directory paths.
    """
    if output_dir is None:
        return [None] * len(fault_events)
    if len(fault_events) == 1:
        return [output_dir]
    output_dirs = [
        os.path.join(output_dir, fault.name or f"fault_{index + 1}")
        for index, fault in enumerate(fault_events)
    ]
    for output_directory in output_dirs:
        os.mkdir(output_directory)
    return output_dirs


def cleanup_empty_fault_output_dir(output_dir: Optional[str], fault_result: EEACResult) -> None:
    """
    Remove per-fault output folder when the fault is empty and no files were produced.

    :param output_dir: Fault output directory.
    :param fault_result: Result for this fault.
    :return: Return value.
    """
    if output_dir is None:
        return
    if fault_result.status != "Empty fault":
        return
    if not os.path.isdir(output_dir):
        return
    if os.listdir(output_dir):
        return
    os.rmdir(output_dir)


def deeac_run(config: Union[EurostagRunConfiguration, DynawoRunConfiguration]) -> EEACResults:
    """
    Main entry point of DEEAC for Eurostag or Dynawo inputs.

    :param config: Run configuration.
    :return: EEAC results.
    """

    _prepare_output_dir(config.output_dir, config.rewrite)

    # try:
    logger = Logger(verbose=config.verbose)
    logger.info("Loading execution plan")
    execution_plan = read_execution_plan(config.execution_tree_file, config.execution_tree)
    # Draw tree if output directory available
    if config.verbose:
        pass

    network = _load_network_from_config(config, logger)
    if len(network.generators) == 0:
        logger.error("EEAC cannot be applied on a network without any generator.")
        logger.print_if_verbose()
        sys.exit(-1)

    output_dirs = build_output_dirs(config.output_dir, network.fault_events)
    if len(network.fault_events) == 1:
        print("One event file specified, no parallelization")
        fault_name, fault_result, per_process_logger = run_fault(
            execution_plan=execution_plan,
            output_dir=output_dirs[0],
            network=network.duplicate(),
            verbose=config.verbose,
            island_threshold=config.island_threshold,
            fault_events=network.fault_events[0],
            warn=config.warn,
        )
        per_process_logger.print_if_verbose()
        critical_results = {fault_name: fault_result}
        cleanup_empty_fault_output_dir(output_dirs[0], fault_result)
    else:

        zipped_data = [
            (
                execution_plan,
                output_path,
                network.duplicate(),
                config.verbose,
                config.island_threshold,
                fault_event,
                config.warn,
            )
            for fault_event, output_path in zip(network.fault_events, output_dirs)
        ]
        critical_results = dict()
        n_jobs = len(zipped_data)

        print(f"Running {len(network.fault_events)} faults in parallel over {config.cores} cores")
        if config.cores == 1:
            for n, data in enumerate(zipped_data):
                print(f"Running fault {n + 1}/{n_jobs}")
                fault_name, fault_result, per_process_logger = run_fault(*data)
                per_process_logger.print_if_verbose()
                critical_results[fault_name] = fault_result
                cleanup_empty_fault_output_dir(data[1], fault_result)
        else:
            results = Parallel(n_jobs=config.cores, backend="loky")(
                delayed(run_fault)(*data) for data in zipped_data
            )
            for i, result in enumerate(results):
                fault_name, fault_result, per_process_logger = result
                per_process_logger.print_if_verbose()
                critical_results[fault_name] = fault_result
                cleanup_empty_fault_output_dir(zipped_data[i][1], fault_result)

    formatted_critical_results = EEACResults()
    for fault in sorted(critical_results.keys()):
        formatted_critical_results.add(fault, critical_results[fault])

    # Save the results in the output folder if specified under a default name
    if config.output_dir is not None:
        config.json_path = os.path.join(config.output_dir, 'critical_cluster_results.json')

    # Save the critical results at the specified location
    if config.json_path is not None:
        json.dump(formatted_critical_results.to_dict(), open(config.json_path, 'w'), indent=2)

    # If neither are specified, don't save
    return formatted_critical_results
