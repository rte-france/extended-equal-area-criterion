# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import os
from datetime import datetime

from deeac.adapters.events.eurostag import EurostagEventParser
from deeac.domain.models import NetworkState, DynamicGenerator
from deeac.domain.models.events.failure import LineShortCircuitEvent
from deeac.domain.models.eeac_tree import EEACTreeNodeIOType
from deeac.domain.services.eeac import EEAC
from deeac.domain.exceptions import DEEACException
from deeac.services import EventLoader


def run_fault_from_args(args):
    return run_parallel_fault(*args)


def run_parallel_fault(
    seq_file, eeac_tree, output_dir, base_network, verbose, duplication_time, network_loading_time,
    tree_loading_time, start_time, parallel_run, island_threshold, protection_delay, warn
):
    """
    Runs the rest of EAC for one fault at a time
    """
    thread_starting_time = datetime.now()
    if parallel_run is True:
        network = base_network.duplicate()
    else:
        network = base_network

    network_initialization_time = datetime.now()

    # Event loader
    event_loader = EventLoader(
        event_parser=EurostagEventParser(
            eurostag_event_file=seq_file,
            protection_delay=protection_delay
        )
    )
    text_result = [f"FAULT: {os.path.splitext(os.path.split(seq_file)[1])[0]}"]
    failure_events, mitigation_events = event_loader.load_events()

    # Checking all protections are triggered at the same time
    fault_name = os.path.splitext(os.path.split(seq_file)[-1])[0]
    if event_loader.event_parser.short_circuit_delay is not None:
        text_result.append("Degraded protection case, cancelling execution")
        print("\n".join(text_result))
        result = {
            "status": "Degraded protection",
            "interval": f"{event_loader.event_parser.short_circuit_delay}ms"
        }
        return fault_name, result

    # Checking the fault is not impedant
    for failure_event in failure_events:
        if isinstance(failure_event, LineShortCircuitEvent):
            fault_resistance = failure_event.fault_resistance
            fault_reactance = failure_event.fault_reactance
            if fault_resistance != 0 or fault_reactance != 0:
                text_result.append("Faults with non-zero impedance are not yet supported, "
                                   "cancelling execution")
                print("\n".join(text_result))
                result = {
                    "status": "Impedant fault"
                }
                return fault_name, result

    # Register time at which all files are loaded
    file_loading_time = datetime.now()
    text_result.append("\nFault events loaded:")
    for i, event in enumerate(failure_events):
        text_result.append(f"\t{i + 1}: {event}")
    text_result.append("Mitigation events loaded:")
    for i, event in enumerate(mitigation_events):
        text_result.append(f"\t{i + 1}: {event}")
    try:
        network.provide_events(failure_events=failure_events, mitigation_events=mitigation_events)
    except IOError as e:
        text_result.append(str(e))
        print("\n".join(text_result))
        return fault_name, "Irrelevant Fault"
    except Exception as e:
        text_result.append(str(e))
        print("\n".join(text_result))
        result = {
            "status": "Error",
            "error_msg": str(e)
        }
        return fault_name, result

    # Register event processing time
    event_processing_time = datetime.now()

    disconnected_buses = {}
    for state in NetworkState:
        try:
            disconnected_buses[state] = network.get_disconnected_buses(state)
        except DEEACException as e:
            text_result.append(str(e))
            print("\n".join(text_result))
            return fault_name, "Irrelevant Fault"

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
        text_result.append(f"Isolated production: {production}MW - {unit_names}")
        if consumption == 0:
            text_result.append(f"No isolated consumption")
        else:
            text_result.append(f"Isolated consumption: {consumption}MW - {load_names}")
        if production > island_threshold:
            text_result.append(f"Islanding over threshold: {production}MW > {island_threshold}MW, cancelling execution")
            print("\n".join(text_result))
            results = {
                "status": "Islanding",
                "production_loss": f"{round(production, 2)}MW",
                "disconnected_production": unit_names,
                "consumption_loss": f"{round(consumption, 2)}MW",
                "disconnected_consumption": load_names
            }
            return fault_name, results
        else:
            text_result.append(f"Islanding below threshold: {production}MW <= {island_threshold}MW, carrying execution")

    elif consumption > 0:
        print(f"WARNING - Isolated consumption: {consumption}MW - {load_names}")

    # Check if buses are disconnected from main network component
    if network.get_disconnected_buses(NetworkState.PRE_FAULT):
        text_result.append(
            "\nWARNING: Buses are disconnected from the main network component (use -v option for details)"
        )

    # Display relevant results
    text_result.append("Reports:\n")

    # Generate EEAC instance
    eeac = EEAC(execution_tree=eeac_tree, network=network, output_dir=output_dir, warn=warn)

    # Provide inputs consisting in post-fault generators
    generators = network.get_state(NetworkState.POST_FAULT).generators
    dynamic_generators = {DynamicGenerator(generator) for generator in generators}
    eeac.provide_inputs({EEACTreeNodeIOType.DYNAMIC_GENERATORS: dynamic_generators})

    # Run EEAC
    report = eeac.run()

    text_result.append(report)
    eeac_processing_time = datetime.now()

    # Get generators disconnected in each state
    generators = {}
    for state in NetworkState:
        generators[state] = {gen.name for gen in network.get_state(state).generators}
    failure_disconnected_generators = generators[NetworkState.PRE_FAULT] - generators[NetworkState.DURING_FAULT]
    mitigation_disconnected_generators = generators[NetworkState.DURING_FAULT] - generators[NetworkState.POST_FAULT]
    if failure_disconnected_generators:
        generator_names = ", ".join(failure_disconnected_generators)
        text_result.append(f"\t* Generators disconnected from the main network component due to the failures: {generator_names}")
    if mitigation_disconnected_generators:
        generator_names = ", ".join(mitigation_disconnected_generators)
        text_result.append(f"\t* Generators disconnected from the main network component due to the mitigations: {generator_names}")

    # Execution times
    execution_tree_time = round((tree_loading_time - start_time).total_seconds(), 3)
    loading_time = round((network_loading_time - tree_loading_time).total_seconds(), 3)
    network_simplification_time = round((duplication_time - network_loading_time).total_seconds(), 3)
    wait_time = round((thread_starting_time - duplication_time).total_seconds(), 3)
    network_copy_time = round((network_initialization_time - thread_starting_time).total_seconds(), 3)
    event_reading_time = round((file_loading_time - network_initialization_time).total_seconds(), 3)
    event_time = round((event_processing_time - file_loading_time).total_seconds(), 3)
    tree_execution_time = round((eeac_processing_time - event_processing_time).total_seconds(), 3)
    text_result.append(
        f"Execution times: {os.path.split(seq_file)[1]}\n"
        f"\t> Input execution tree file reading: {execution_tree_time} seconds\n"
        f"\t> Input network files reading: {loading_time} seconds\n"
        f"\t> Network simplification time: {network_simplification_time} seconds\n"
        f"\t> Thread waiting time: {wait_time} seconds\n"
        f"\t> Network duplication time: {network_copy_time} seconds\n"
        f"\t> Input event files reading: {event_reading_time} seconds\n"
        f"\t> Event processing: {event_time} seconds\n"
        f"\t> EEAC tree execution: {tree_execution_time} seconds\n"
    )

    # Display additional results
    if verbose:
        # Buses initially disconnected
        if disconnected_buses[NetworkState.PRE_FAULT]:
            buses = ', '.join(disconnected_buses[NetworkState.PRE_FAULT])
            text_result.append(f"\t* Buses disconnected from the main network component: {buses}")

    # Print all the outputs at once so the parallel executions don't overlay on each other
    print("\n".join(text_result))
    return fault_name, eeac.critical_result
