"""High-level EEAC workflows for Eurostag and Dynawo inputs.

:module: workflows
"""
# Copyright (c) 2020-2026, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from xml.etree import ElementTree as ET

from deeac.IO.arguments_parser import DynawoRunConfiguration, EurostagRunConfiguration
from deeac.DynawoPostProcess.runner import DynawoProcessResult, DynawoRunner
from deeac.IO.dynawo.patch_files import (
    DynawoFaultEventDescription,
    DynawoPatchedScenarioFiles,
    build_scenario_dyd_tree,
    build_scenario_par_tree,
    build_multiple_jobs_tree,
    indent_xml,
    write_xml_tree,
)
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
from deeac.IO.plan_loader import read_execution_plan
from deeac.IO.eurostag.events.event_parser import EurostagEventParser
from deeac.Models.events.branch_event import BranchEvent
from deeac.Models.events.bus_short_circuit_clearing_event import BusShortCircuitClearingEvent
from deeac.Models.events.bus_short_circuit_event import BusShortCircuitEvent
from deeac.Models.events.fault_events import FaultEvents
from deeac.Models.events.line_short_circuit_clearing_event import LineShortCircuitClearingEvent
from deeac.Models.events.line_short_circuit_event import LineShortCircuitEvent
from deeac.Models.network import Network
from deeac.Simulations.results import EEACResult, EEACResults
from deeac.Utils.logger import Logger
from deeac.enums import BreakerPosition
from deeac.deeac_all_paths import (
    _prepare_output_dir,
    build_output_dirs,
    cleanup_empty_fault_output_dir,
    deeac_run,
    run_fault,
)


def run_eurostag_workflow(config: EurostagRunConfiguration) -> EEACResults:
    """Run EEAC using Eurostag network and sequence files.

    :param config: Eurostag network, sequence, plan, and output configuration.
    :return: Results containing one entry per sequence file.
    """
    ensure_execution_plan(config)
    return deeac_run(config)


def run_eurostag_to_dynawo_workflow(
    config: EurostagRunConfiguration,
    dynawo_jobs_file: str,
    generation_dir: str,
    selected_fault_ids: Optional[Sequence[str]] = None,
    line_fault_model_available: bool = True,
    use_multiple_jobs: bool = False,
) -> tuple[EEACResults, List[str]]:
    """Run Eurostag EEAC, then map its sequence events into Dynawo cases.

    Eurostag sequence files are the only fault source. Each selected line
    fault is matched to an IIDM line by its endpoint buses and parallel ID.
    Temporary JSON is used internally to reuse the Dynawo case writer and is
    deleted after generation; users do not provide a second fault catalogue.

    :param config: Eurostag network, sequence, plan, and result configuration.
    :param dynawo_jobs_file: Base Dynawo JOBS file used for generated cases.
    :param generation_dir: Directory receiving generated Dynawo case folders.
    :param selected_fault_ids: Fault IDs to prepare, or ``None`` to prepare
        every fault that has an EEAC result.
    :param line_fault_model_available: Whether Dynawo provides its LineFault model.
    :param use_multiple_jobs: Generate a Dynawo multiple-jobs case when supported.
    :return: Eurostag EEAC results and paths to generated Dynawo cases.
    """
    results: EEACResults = run_eurostag_workflow(config)
    result_fault_ids: set[str] = set()
    for result_entry in results.results:
        result_fault_ids.add(result_entry.fault_name)
    if selected_fault_ids is None:
        faults_to_prepare: Sequence[str] = sorted(result_fault_ids)
    else:
        faults_to_prepare = selected_fault_ids
        validate_selected_fault_ids(result_fault_ids, faults_to_prepare)
    with tempfile.TemporaryDirectory(prefix="deeac_eurostag_dynawo_") as temporary_dir:
        derived_fault_files: List[str] = derive_dynawo_fault_json_from_eurostag(
            config=config,
            jobs_file=dynawo_jobs_file,
            selected_fault_ids=faults_to_prepare,
            temporary_dir=Path(temporary_dir),
        )
        generated_folders: List[str] = prepare_dynawo_line_fault_cases(
            jobs_file=dynawo_jobs_file,
            fault_files=derived_fault_files,
            output_dir=generation_dir,
            selected_fault_ids=faults_to_prepare,
            line_fault_model_available=line_fault_model_available,
            use_multiple_jobs=use_multiple_jobs,
        )
    return results, generated_folders


def derive_dynawo_fault_json_from_eurostag(
    config: EurostagRunConfiguration,
    jobs_file: str,
    selected_fault_ids: Sequence[str],
    temporary_dir: Path,
) -> List[str]:
    """Map selected Eurostag line-fault sequences to temporary Dynawo JSON.

    :param config: Eurostag configuration containing the sequence file paths.
    :param jobs_file: Dynawo JOBS file whose IIDM line IDs are used for mapping.
    :param selected_fault_ids: Sequence file stems selected for case creation.
    :param temporary_dir: Directory for temporary JSON consumed by the case writer.
    :return: Temporary JSON file paths, in selected fault order.
    :raises ValueError: If a sequence cannot be matched to a supported IIDM line.
    """
    jobs_path: Path = Path(jobs_file).resolve()
    jobs_root: ET.Element = ET.parse(jobs_path).getroot()
    iidm_path: Optional[Path] = None
    for element in jobs_root.iter():
        iidm_reference: Optional[str] = element.get("iidmFile")
        if iidm_reference is not None:
            iidm_path = (jobs_path.parent / iidm_reference).resolve()
        else:
            pass
    if iidm_path is None or not iidm_path.is_file():
        raise ValueError(f"Could not resolve the IIDM file from {jobs_path}.")
    else:
        pass

    iidm_root: ET.Element = ET.parse(iidm_path).getroot()
    voltage_level_names: dict[str, str] = dict()
    for voltage_level in iidm_root.iter():
        if voltage_level.tag.rsplit("}", 1)[-1] == "voltageLevel":
            voltage_level_name: Optional[str] = voltage_level.get("name")
            voltage_level_id: Optional[str] = voltage_level.get("id")
            if voltage_level_name is not None and voltage_level_name.endswith("_VL"):
                bus_name: str = voltage_level_name[:-3]
                if voltage_level_id is not None:
                    voltage_level_names[voltage_level_id] = bus_name
                else:
                    pass
            else:
                pass
        else:
            pass

    iidm_lines: List[dict[str, str]] = list()
    for line in iidm_root.iter():
        if line.tag.rsplit("}", 1)[-1] == "line":
            line_id: Optional[str] = line.get("id")
            terminal_1: Optional[str] = line.get("bus1")
            terminal_2: Optional[str] = line.get("bus2")
            voltage_level_1: Optional[str] = line.get("voltageLevelId1")
            voltage_level_2: Optional[str] = line.get("voltageLevelId2")
            if (line_id is not None and terminal_1 is not None and terminal_2 is not None
                    and voltage_level_1 is not None and voltage_level_2 is not None):
                if voltage_level_1 in voltage_level_names and voltage_level_2 in voltage_level_names:
                    id_without_suffix: str = line_id.removesuffix("_AC")
                    parallel_id: str = id_without_suffix.rsplit("-", 1)[-1]
                    iidm_lines.append({
                        "static_id": line_id,
                        "terminal_1": terminal_1,
                        "terminal_2": terminal_2,
                        "first_bus": voltage_level_names[voltage_level_1],
                        "second_bus": voltage_level_names[voltage_level_2],
                        "parallel_id": parallel_id,
                    })
                else:
                    pass
            else:
                pass
        else:
            pass

    seq_paths: dict[str, Path] = dict()
    for seq_file in config.seq_files:
        seq_path: Path = Path(seq_file)
        seq_paths[seq_path.stem] = seq_path
    generated_files: List[str] = list()
    for fault_id in selected_fault_ids:
        if fault_id not in seq_paths:
            raise ValueError(f"No Eurostag sequence file matches fault ID: {fault_id}")
        else:
            pass
        events: List[object] = EurostagEventParser(str(seq_paths[fault_id])).parse_events()
        line_faults: List[LineShortCircuitEvent] = list()
        branch_events: List[BranchEvent] = list()
        for event in events:
            if isinstance(event, LineShortCircuitEvent):
                line_faults.append(event)
            elif isinstance(event, BranchEvent) and not event.breaker_closed:
                branch_events.append(event)
            else:
                pass
        if len(line_faults) != 1:
            raise ValueError(f"Fault {fault_id}: only one line fault per sequence is currently supported.")
        else:
            line_fault: LineShortCircuitEvent = line_faults[0]
        if line_fault.fault_resistance != 0.0 or line_fault.fault_reactance != 0.0:
            raise ValueError(f"Fault {fault_id}: non-zero line-fault impedance is not supported.")
        else:
            pass
        matching_lines: List[dict[str, str]] = list()
        for iidm_line in iidm_lines:
            same_buses: bool = (
                iidm_line["first_bus"] == line_fault.first_bus_name
                and iidm_line["second_bus"] == line_fault.second_bus_name
            ) or (
                iidm_line["first_bus"] == line_fault.second_bus_name
                and iidm_line["second_bus"] == line_fault.first_bus_name
            )
            if same_buses and iidm_line["parallel_id"] == line_fault.parallel_id:
                matching_lines.append(iidm_line)
            else:
                pass
        if len(matching_lines) != 1:
            raise ValueError(f"Fault {fault_id}: expected one matching IIDM line, found {len(matching_lines)}.")
        else:
            iidm_line = matching_lines[0]
        matching_trips: List[BranchEvent] = list()
        for branch_event in branch_events:
            same_buses = (
                branch_event.first_bus_name == line_fault.first_bus_name
                and branch_event.second_bus_name == line_fault.second_bus_name
            ) or (
                branch_event.first_bus_name == line_fault.second_bus_name
                and branch_event.second_bus_name == line_fault.first_bus_name
            )
            if same_buses and branch_event.parallel_id == line_fault.parallel_id:
                matching_trips.append(branch_event)
            else:
                raise ValueError(f"Fault {fault_id}: extra branch trips are not supported yet.")
        if len(matching_trips) != 2 or matching_trips[0].time != matching_trips[1].time:
            raise ValueError(f"Fault {fault_id}: expected both ends of the faulted line to trip together.")
        else:
            pass
        end_time: float = matching_trips[0].time
        if line_fault.first_bus_name == iidm_line["first_bus"]:
            distance: float = line_fault.fault_position
        else:
            distance = 1.0 - line_fault.fault_position
        fault_data: dict[str, object] = {
            "fault_id": fault_id,
            "fault_type": "line",
            "target": {
                "first_bus": iidm_line["first_bus"],
                "second_bus": iidm_line["second_bus"],
                "parallel_id": iidm_line["parallel_id"],
                "static_id": iidm_line["static_id"],
                "terminal_1": iidm_line["terminal_1"],
                "terminal_2": iidm_line["terminal_2"],
            },
            "impedance": {"r": 0.0, "x": 0.0},
            "start_time": line_fault.time,
            "end_time": end_time,
            "distance": distance,
            "disconnections": [{
                "first_bus": iidm_line["first_bus"],
                "second_bus": iidm_line["second_bus"],
                "parallel_id": iidm_line["parallel_id"],
                "time": end_time,
            }],
        }
        fault_path: Path = temporary_dir / f"{fault_id}.json"
        with fault_path.open("w", encoding="utf-8") as fault_file:
            json.dump(fault_data, fault_file, indent=2)
        generated_files.append(str(fault_path))
    return generated_files


def run_dynawo_workflow(
    config: DynawoRunConfiguration,
    fault_files: Sequence[str] | str,
) -> EEACResults:
    """Run EEAC on a Dynawo network using separate fault JSON files.

    The source ``.iidm``, ``.dyd``, and ``.par`` files are read but never
    modified. Each JSON file describes exactly one fault and uses this schema::

        {
          "fault_id": "line_fault_1",
          "fault_type": "line" | "node",
          "target": {"first_bus": "BUS_A", "second_bus": "BUS_B",
                     "parallel_id": "1"} | {"bus": "BUS_A"},
          "impedance": {"r": 0.0, "x": 0.0},
          "start_time": 1.0,
          "end_time": 1.1,
          "distance": 0.5,
          "disconnections": [{"first_bus": "BUS_A", "second_bus": "BUS_B",
                               "parallel_id": "1", "time": 1.1}]
        }

    ``distance`` is required for line faults and is a fraction from the first
    bus (0 through 1). ``disconnections`` is required and lists each branch to
    open after the fault, using its two DEEAC bus names, parallel ID, and trip
    time. Both branch ends are opened. Automatic IIDM breaker-propagation rules
    are not inferred by this first implementation.
    Non-zero line-fault impedance is rejected because the current EEAC line
    fault model does not support it.

    :param config: Dynawo network, plan, and output configuration.
    :param fault_files: One JSON file, a directory of JSON files, or an explicit
        sequence of JSON file paths.
    :return: Results containing one entry per fault file.
    :raises ValueError: If a fault file is invalid or requests an unsupported
        event representation.
    """
    from deeac.IO.dynawo.parse_dynawo import parse_dynawo_configuration

    ensure_execution_plan(config)
    execution_plan = read_execution_plan(config.execution_tree_file, config.execution_tree)
    network: Network = parse_dynawo_configuration(config)
    fault_events: List[FaultEvents] = list()
    fault_ids: set[str] = set()
    resolved_fault_files: List[str] = resolve_fault_files(fault_files)
    iidm_file: Path = resolve_iidm_file(config)
    for fault_file in resolved_fault_files:
        fault_event: FaultEvents = parse_dynawo_fault_json(Path(fault_file), iidm_file)
        if fault_event.name in fault_ids:
            raise ValueError(f"Duplicate fault_id in Dynawo fault files: {fault_event.name}")
        else:
            fault_ids.add(fault_event.name)
            fault_events.append(fault_event)
    if len(fault_events) == 0:
        raise ValueError("At least one Dynawo fault JSON file is required.")
    else:
        network.set_fault_events(fault_events)

    _prepare_output_dir(config.output_dir, config.rewrite)
    output_dirs: List[Optional[str]] = build_output_dirs(config.output_dir, fault_events)
    results_by_name: dict[str, EEACResult] = dict()
    for fault_index, fault_event in enumerate(fault_events):
        logger: Logger
        fault_name, result, logger = run_fault(
            execution_plan=execution_plan,
            output_dir=output_dirs[fault_index],
            network=network.duplicate(),
            verbose=config.verbose,
            island_threshold=config.island_threshold,
            fault_events=fault_event,
            warn=config.warn,
        )
        logger.print_if_verbose()
        results_by_name[fault_name] = result
        cleanup_empty_fault_output_dir(output_dirs[fault_index], result)

    results: EEACResults = EEACResults()
    for fault_name in sorted(results_by_name):
        results.add(fault_name, results_by_name[fault_name])

    if config.output_dir is not None:
        config.json_path = os.path.join(config.output_dir, "critical_cluster_results.json")
    else:
        pass
    if config.json_path is not None:
        with open(config.json_path, "w", encoding="utf-8") as result_file:
            json.dump(results.to_dict(), result_file, indent=2)
    else:
        pass
    return results


def run_dynawo_simulation_workflow(
    config: DynawoRunConfiguration,
    fault_files: Sequence[str] | str,
    jobs_file: str,
    generation_dir: str,
    selected_fault_ids: Optional[Sequence[str]] = None,
    line_fault_model_available: bool = True,
    use_multiple_jobs: bool = False,
) -> tuple[EEACResults, List[str]]:
    """Run Dynawo EEAC and prepare selected line-fault simulation cases.

    Pass ``None`` for ``selected_fault_ids`` to prepare every fault. To prepare
    only critical faults, pass the fault IDs selected from the EEAC results.

    :param config: Dynawo network, plan, and EEAC output configuration.
    :param fault_files: Standalone fault JSON files used by EEAC.
    :param jobs_file: Base Dynawo JOBS file to copy for simulation cases.
    :param generation_dir: Directory receiving one generated case per fault.
    :param selected_fault_ids: Faults to prepare, or ``None`` for all.
    :param line_fault_model_available: Whether Dynawo provides its LineFault model.
    :param use_multiple_jobs: Generate a Dynawo multiple-jobs case when supported.
    :return: EEAC results and generated case directory paths.
    :raises ValueError: If a selected result has no matching fault file or
        case generation encounters an unsupported fault type.
    """
    results: EEACResults = run_dynawo_workflow(config, fault_files)
    if selected_fault_ids is not None:
        result_fault_ids: set[str] = set()
        for result_entry in results.results:
            result_fault_ids.add(result_entry.fault_name)
        validate_selected_fault_ids(result_fault_ids, selected_fault_ids)
    else:
        pass
    generated_folders: List[str] = prepare_dynawo_line_fault_cases(
        jobs_file=jobs_file,
        fault_files=fault_files,
        output_dir=generation_dir,
        selected_fault_ids=selected_fault_ids,
        line_fault_model_available=line_fault_model_available,
        use_multiple_jobs=use_multiple_jobs,
    )
    if selected_fault_ids is not None:
        generated_ids: set[str] = set()
        for generated_folder in generated_folders:
            if use_multiple_jobs:
                multiple_file: Path = Path(generated_folder) / f"{Path(jobs_file).stem}.multiple"
                for element in ET.parse(multiple_file).getroot().iter():
                    if element.tag.rsplit("}", 1)[-1] == "scenario" and element.get("id") is not None:
                        generated_ids.add(element.get("id"))
                    else:
                        pass
            else:
                generated_ids.add(Path(generated_folder).name)
        for selected_fault_id in selected_fault_ids:
            selected_folder_name: str = re.sub(r"[^A-Za-z0-9_.-]", "_", selected_fault_id)
            if selected_folder_name not in generated_ids:
                raise ValueError(f"Selected fault has no generated Dynawo case: {selected_fault_id}")
            else:
                pass
    else:
        pass
    return results, generated_folders


def run_generated_dynawo_cases(
    generated_folders: Sequence[str],
    jobs_file: str,
    dynawo_install_dir: str,
    timeout_seconds: Optional[float] = None,
) -> List[DynawoProcessResult]:
    """Run each generated case with the installed Dynawo executable.

    :param generated_folders: Isolated case directories returned by a workflow.
    :param jobs_file: Original jobs file, used to locate its copied name.
    :param dynawo_install_dir: Dynawo installation directory.
    :param timeout_seconds: Optional timeout per case.
    :return: Process results in the same order as the case directories.
    """
    runner: DynawoRunner = DynawoRunner(dynawo_install_dir=dynawo_install_dir)
    results: List[DynawoProcessResult] = list()
    for folder in generated_folders:
        copied_jobs: Path = Path(folder) / Path(jobs_file).name
        results.append(runner.run_jobs_file(str(copied_jobs), timeout_seconds))
    return results


def validate_selected_fault_ids(
    available_fault_ids: set[str],
    selected_fault_ids: Sequence[str],
) -> None:
    """Ensure requested post-EEAC faults exist in the EEAC result set.

    :param available_fault_ids: IDs for which EEAC produced results.
    :param selected_fault_ids: IDs requested for Dynawo preparation.
    :return: Return value.
    :raises ValueError: If a selected ID has no EEAC result.
    """
    for selected_fault_id in selected_fault_ids:
        if selected_fault_id not in available_fault_ids:
            raise ValueError(f"Selected fault has no EEAC result: {selected_fault_id}")
        else:
            pass


def ensure_execution_plan(
    config: EurostagRunConfiguration | DynawoRunConfiguration,
) -> None:
    """Use the built-in EEAC plan when the caller supplied no plan.

    :param config: Eurostag or Dynawo run configuration.
    :return: Return value.
    """
    if config.execution_tree is None and config.execution_tree_file is None:
        config.execution_tree = default_execution_plan()
    else:
        pass


def default_execution_plan() -> ExecutionPlan:
    """Build the standard EEAC identifier, evaluator, and selector plan.

    :return: The in-memory equivalent of the repository's standard EEAC plan.
    """
    identifier: ExecutionNode = ExecutionNode(
        node_type="CriticalClustersIdentifier",
        node_id=0,
        name="Critical clusters identifier",
        identifier_config=IdentifierConfig(
            identifier_type="DFT",
            during_fault_identification_time_step=170.0,
            significant_angle_variation_threshold=5.0,
            tso_customization="RTE",
            max_number_candidates=12,
        ),
    )
    evaluator: ExecutionNode = ExecutionNode(
        node_type="CriticalClustersEvaluator",
        node_id=1,
        name="Critical clusters evaluator",
        evaluator_config=EvaluatorConfig(
            evaluation_sequence=EvaluationSequence(
                nodes=[
                    EvaluationNode(node_type="OMIB", omib_config=OMIBConfig(omib_type="ZOOMIB")),
                    EvaluationNode(
                        node_type="EAC",
                        eac_config=EACConfig(angle_increment=0.1, max_integration_angle=270.0),
                    ),
                    EvaluationNode(
                        node_type="OMIBTrajectoryCalculator",
                        trajectory_config=OMIBTrajectoryConfig(
                            calculator_type="TAYL",
                            critical_angle_shift=4.0,
                        ),
                    ),
                ]
            )
        ),
    )
    selector: ExecutionNode = ExecutionNode(
        node_type="CriticalClusterSelector",
        node_id=2,
        name="Critical cluster selector",
        selector_config=SelectorConfig(selector_type="MIN"),
    )
    return ExecutionPlan(nodes=[identifier, evaluator, selector])


def parse_dynawo_fault_json(fault_file: Path, iidm_file: Optional[Path] = None) -> FaultEvents:
    """Parse one Dynawo fault JSON file into EEAC failure and mitigation events.

    :param fault_file: JSON file following :func:`run_dynawo_workflow` schema.
    :param iidm_file: Optional IIDM source used to derive default trips.
    :return: Fault event bundle named with ``fault_id``.
    :raises ValueError: If required fields or supported target details are
        missing or invalid.
    """
    try:
        with fault_file.open(encoding="utf-8") as json_file:
            raw_fault: object = json.load(json_file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read Dynawo fault JSON {fault_file}: {error}") from error

    if not isinstance(raw_fault, dict):
        raise ValueError(f"Dynawo fault JSON must contain an object: {fault_file}")
    else:
        fault: dict[str, object] = raw_fault

    fault_id: str = require_string(fault, "fault_id", fault_file)
    fault_type: str = require_string(fault, "fault_type", fault_file).lower()
    if fault_type in ("line_fault", "linefault"):
        fault_type = "line"
    elif fault_type in ("node_fault", "nodefault"):
        fault_type = "node"
    elif fault_type in ("transformer_fault", "transformerfault"):
        fault_type = "transformer"
    else:
        pass
    target: object = fault.get("target")
    if not isinstance(target, dict):
        raise ValueError(f"Fault {fault_id}: target must be an object.")
    else:
        target_data: dict[str, object] = target

    impedance: object = fault.get("impedance", dict())
    if not isinstance(impedance, dict):
        raise ValueError(f"Fault {fault_id}: impedance must be an object.")
    else:
        impedance_data: dict[str, object] = impedance
    resistance: float = require_number(impedance_data, "r", fault_id, 0.0)
    reactance: float = require_number(impedance_data, "x", fault_id, 0.0)
    start_time: float = require_number(fault, "start_time", fault_id)
    end_time: float = require_number(fault, "end_time", fault_id)
    if end_time <= start_time:
        raise ValueError(f"Fault {fault_id}: end_time must be later than start_time.")
    else:
        pass

    failures: List[object] = list()
    mitigations: List[object] = list()
    if fault_type == "node" or fault_type == "transformer":
        bus_name: str = require_string(target_data, "bus", fault_file)
        failures.append(
            BusShortCircuitEvent(
                time=start_time,
                bus_name=bus_name,
                fault_resistance=resistance,
                fault_reactance=reactance,
            )
        )
        mitigations.append(BusShortCircuitClearingEvent(time=end_time, bus_name=bus_name))
    elif fault_type == "line":
        first_bus: str = require_string(target_data, "first_bus", fault_file)
        second_bus: str = require_string(target_data, "second_bus", fault_file)
        parallel_id: str = require_string(target_data, "parallel_id", fault_file)
        distance: float = require_number(fault, "distance", fault_id)
        if distance <= 0.0 or distance >= 1.0:
            raise ValueError(f"Fault {fault_id}: distance must be strictly between 0 and 1.")
        elif resistance != 0.0 or reactance != 0.0:
            raise ValueError(f"Fault {fault_id}: EEAC does not support non-zero line-fault impedance yet.")
        else:
            pass
        failures.append(
            LineShortCircuitEvent(
                time=start_time,
                first_bus_name=first_bus,
                second_bus_name=second_bus,
                parallel_id=parallel_id,
                fault_position=distance,
                fault_resistance=resistance,
                fault_reactance=reactance,
            )
        )
        mitigations.append(
            LineShortCircuitClearingEvent(
                time=end_time,
                first_bus_name=first_bus,
                second_bus_name=second_bus,
                parallel_id=parallel_id,
            )
        )
    else:
        pass

    disconnections: object = fault.get("disconnections")
    if disconnections is None:
        common_disconnection_time: float = require_number(fault, "disconnection_time", fault_id)
        if iidm_file is None:
            raise ValueError(f"Fault {fault_id}: IIDM input is required to derive default disconnections.")
        else:
            disconnections = derive_default_disconnections(
                iidm_file=iidm_file,
                fault_type=fault_type,
                target_data=target_data,
                disconnection_time=common_disconnection_time,
            )
    elif not isinstance(disconnections, list):
        raise ValueError(f"Fault {fault_id}: disconnections must be a list.")
    else:
        pass
    disconnected_branches: List[tuple[str, str, str]] = list()
    for disconnection_index, disconnection in enumerate(disconnections):
        if not isinstance(disconnection, dict):
            raise ValueError(f"Fault {fault_id}: disconnection {disconnection_index} must be an object.")
        else:
            disconnection_data: dict[str, object] = disconnection
        first_bus_name: str = require_string(disconnection_data, "first_bus", fault_file)
        second_bus_name: str = require_string(disconnection_data, "second_bus", fault_file)
        branch_parallel_id: str = require_string(disconnection_data, "parallel_id", fault_file)
        disconnected_branches.append((first_bus_name, second_bus_name, branch_parallel_id))
        disconnection_time: float = require_number(disconnection_data, "time", fault_id)
        if disconnection_time < end_time:
            raise ValueError(f"Fault {fault_id}: disconnection time cannot be before fault clearing.")
        else:
            pass
        mitigations.append(
            BranchEvent(
                time=disconnection_time,
                first_bus_name=first_bus_name,
                second_bus_name=second_bus_name,
                parallel_id=branch_parallel_id,
                breaker_position=BreakerPosition.FIRST_BUS,
            )
        )
        mitigations.append(
            BranchEvent(
                time=disconnection_time,
                first_bus_name=first_bus_name,
                second_bus_name=second_bus_name,
                parallel_id=branch_parallel_id,
                breaker_position=BreakerPosition.SECOND_BUS,
            )
        )

    if fault_type == "line":
        target_branch_found: bool = False
        for disconnected_branch in disconnected_branches:
            same_bus_pair: bool = (
                disconnected_branch[0] == first_bus
                and disconnected_branch[1] == second_bus
            ) or (
                disconnected_branch[0] == second_bus
                and disconnected_branch[1] == first_bus
            )
            same_parallel_id: bool = disconnected_branch[2] == parallel_id
            if same_bus_pair and same_parallel_id:
                target_branch_found = True
            else:
                pass
        if not target_branch_found:
            raise ValueError(f"Fault {fault_id}: disconnections must include the faulted line segment.")
        else:
            pass
    elif fault_type == "transformer":
        transformer_id: str = require_string(target_data, "transformer_id", fault_file)
        transformer_trip_found: bool = False
        for disconnection in disconnections:
            if isinstance(disconnection, dict) and disconnection.get("static_id") == transformer_id:
                transformer_trip_found = True
            else:
                pass
        if not transformer_trip_found:
            raise ValueError(f"Fault {fault_id}: transformer disconnections must include target.transformer_id.")
        else:
            pass
    elif fault_type == "node":
        pass
    else:
        raise ValueError(f"Fault {fault_id}: supported fault_type values are 'node', 'transformer', and 'line'.")

    return FaultEvents(
        failure_events=failures,
        mitigation_events=mitigations,
        name=fault_id,
    )


def derive_default_disconnections(
    iidm_file: Path,
    fault_type: str,
    target_data: dict[str, object],
    disconnection_time: float,
) -> List[dict[str, object]]:
    """Derive the faulted branch trip for a simple bus-breaker case.

    :param iidm_file: IIDM network that defines bus-breaker topology.
    :param fault_type: Normalized fault type.
    :param target_data: JSON target object for the fault.
    :param disconnection_time: Common clearing-trip time in seconds.
    :return: Explicit EEAC/Dynawo disconnection records.
    """
    root: ET.Element = ET.parse(iidm_file).getroot()
    branch_tags: set[str] = {"line", "twoWindingsTransformer"}
    if fault_type == "node":
        raise ValueError("Node faults require explicit disconnections; automatic equipment trips are not implemented.")
    else:
        pass
    branch_buses: Dict[str, tuple[str, str]] = dict()
    bus_names: Dict[str, str] = dict()
    voltage_level_names: Dict[str, str] = dict()
    for element in root.iter():
        tag_name: str = element.tag.rsplit("}", 1)[-1]
        if tag_name == "voltageLevel":
            if element.get("topologyKind") == "NODE_BREAKER":
                raise ValueError("Node-breaker cases require explicit disconnections.")
            else:
                pass
            voltage_level_id: Optional[str] = element.get("id")
            voltage_level_name: Optional[str] = element.get("name")
            if voltage_level_id is not None and voltage_level_name is not None:
                voltage_level_names[voltage_level_id] = voltage_level_name.removesuffix("_VL")
            else:
                pass
        elif tag_name == "bus":
            bus_id: Optional[str] = element.get("id")
            if bus_id is not None:
                bus_names[bus_id] = bus_id
            else:
                pass
        elif tag_name == "switch":
            raise ValueError("Cases with switches require explicit disconnections.")
        elif tag_name in branch_tags:
            branch_id: Optional[str] = element.get("id")
            first_bus: Optional[str] = element.get("bus1")
            second_bus: Optional[str] = element.get("bus2")
            if branch_id is not None and first_bus is not None and second_bus is not None:
                branch_buses[branch_id] = (first_bus, second_bus)
                first_voltage_level: Optional[str] = element.get("voltageLevelId1")
                second_voltage_level: Optional[str] = element.get("voltageLevelId2")
                if first_voltage_level in voltage_level_names:
                    bus_names[first_bus] = voltage_level_names[first_voltage_level]
                else:
                    pass
                if second_voltage_level in voltage_level_names:
                    bus_names[second_bus] = voltage_level_names[second_voltage_level]
                else:
                    pass
            else:
                pass
        else:
            pass
    if fault_type == "line":
        start_branch_id: str = require_string(target_data, "static_id", iidm_file)
        start_buses: tuple[str, str] = branch_buses.get(start_branch_id, ("", ""))
        if start_buses == ("", ""):
            raise ValueError(f"Faulted IIDM line is missing: {start_branch_id}")
        else:
            selected_branch_ids: set[str] = {start_branch_id}
    elif fault_type == "transformer":
        start_branch_id = require_string(target_data, "transformer_id", iidm_file)
        start_buses = branch_buses.get(start_branch_id, ("", ""))
        if start_buses == ("", ""):
            raise ValueError(f"Faulted IIDM transformer is missing: {start_branch_id}")
        else:
            selected_branch_ids = {start_branch_id}
    else:
        raise ValueError(f"Unsupported automatic disconnection fault type: {fault_type}")
    result: List[dict[str, object]] = list()
    for branch_id in sorted(selected_branch_ids):
        first_bus, second_bus = branch_buses[branch_id]
        branch_name: str = branch_id.removesuffix("_AC").removesuffix("_PT")
        parallel_id: str = branch_name.rsplit("-", 1)[-1]
        result.append(dict(first_bus=bus_names[first_bus], second_bus=bus_names[second_bus], parallel_id=parallel_id, static_id=branch_id, time=disconnection_time))
    return result


def resolve_iidm_file(config: DynawoRunConfiguration) -> Path:
    """Resolve the IIDM source file from a Dynawo run configuration.

    :param config: Dynawo case configuration.
    :return: Existing IIDM input path.
    """
    if config.iidm_file is not None:
        iidm_file: Path = Path(config.iidm_file)
    elif config.jobs_file is not None:
        jobs_file: Path = Path(config.jobs_file)
        jobs_root: ET.Element = ET.parse(jobs_file).getroot()
        iidm_reference: Optional[str] = None
        for element in jobs_root.iter():
            value: Optional[str] = element.get("iidmFile")
            if value is not None:
                iidm_reference = value
            else:
                pass
        if iidm_reference is None:
            raise ValueError(f"Could not resolve IIDM input from {jobs_file}.")
        else:
            iidm_file = jobs_file.parent / iidm_reference
    else:
        raise ValueError("Dynawo default disconnections require an IIDM or JOBS input.")
    if iidm_file.is_file():
        return iidm_file
    else:
        raise ValueError(f"Dynawo IIDM input does not exist: {iidm_file}")


def prepare_dynawo_line_fault_cases(
    jobs_file: str,
    fault_files: Sequence[str] | str,
    output_dir: str,
    selected_fault_ids: Optional[Sequence[str]] = None,
    line_fault_model_available: bool = True,
    use_multiple_jobs: bool = False,
) -> List[str]:
    """Create one copied Dynawo input folder for each selected line fault.

    The source case folder is copied once per selected fault. The copied DYD
    retains the original dynamic models and receives the line-fault and line
    clearing models; a scenario-specific PAR file supplies their values. The
    copied JOBS file continues to reference the copied base inputs.

    The default output is one copied case folder per fault. Set
    ``use_multiple_jobs`` when the installed Dynawo algorithm accepts a
    multiple-jobs file. Set ``line_fault_model_available`` to ``False`` to
    replace line faults with an IIDM split and a NodeFault at the split point.

    A line fault JSON uses the EEAC schema plus these target fields::

        "target": {
          "first_bus": "BUS_A", "second_bus": "BUS_B",
          "parallel_id": "1", "static_id": "IIDM_LINE_ID",
          "terminal_1": "TERMINAL_A", "terminal_2": "TERMINAL_B"
        }

    :param jobs_file: Source Dynawo ``.jobs`` file.
    :param fault_files: JSON descriptions, one per fault.
    :param output_dir: New root directory for generated case folders.
    :param selected_fault_ids: Fault IDs to prepare. ``None`` selects every
        supplied fault; pass IDs selected as critical by the caller otherwise.
    :param line_fault_model_available: Whether this Dynawo version provides
        ``LineFault``.
    :param use_multiple_jobs: Generate one scenario-specific DYD/PAR pair and
        one multiple-jobs XML file instead of one copied case per fault.
    :return: Paths to the generated case folders.
    :raises ValueError: If inputs are invalid, unsupported, or would overwrite
        existing output.
    """
    source_jobs: Path = Path(jobs_file).resolve()
    source_dir: Path = source_jobs.parent
    case_output_dir: Path = Path(output_dir).resolve()
    if not source_jobs.is_file():
        raise ValueError(f"Dynawo jobs file does not exist: {source_jobs}")
    else:
        pass
    if case_output_dir == source_dir or source_dir in case_output_dir.parents:
        raise ValueError("Dynawo output directory must be outside the source case directory.")
    else:
        pass

    selected_ids: Optional[set[str]] = None
    if selected_fault_ids is not None:
        selected_ids = set(selected_fault_ids)
    else:
        pass
    source_jobs_root: ET.Element = ET.parse(source_jobs).getroot()
    source_dyd_file: Optional[Path] = None
    source_iidm_file: Optional[Path] = None
    for element in source_jobs_root.iter():
        iidm_reference: Optional[str] = element.get("iidmFile")
        if iidm_reference is not None:
            source_iidm_file = (source_dir / iidm_reference).resolve()
        else:
            pass
        if element.tag.rsplit("}", 1)[-1] == "dynModels":
            dyd_reference: Optional[str] = element.get("dydFile")
            if dyd_reference is not None:
                source_dyd_file = (source_dir / dyd_reference).resolve()
            else:
                pass
        else:
            pass
    if source_dyd_file is None or not source_dyd_file.is_file():
        raise ValueError(f"Could not resolve the DYD file from {source_jobs}.")
    elif source_iidm_file is None or not source_iidm_file.is_file():
        raise ValueError(f"Could not resolve the IIDM file from {source_jobs}.")
    else:
        pass
    validate_case_file_references(source_jobs_root, source_dir, "JOBS")
    source_dyd_root: ET.Element = ET.parse(source_dyd_file).getroot()
    validate_case_file_references(source_dyd_root, source_dyd_file.parent, "DYD")

    case_output_dir.mkdir(parents=True, exist_ok=True)
    generated_folders: List[str] = list()
    parsed_faults: List[DynawoFaultEventDescription] = list()
    generated_names: set[str] = set()
    resolved_fault_files: List[str] = resolve_fault_files(fault_files)
    for fault_path in resolved_fault_files:
        fault_file: Path = Path(fault_path)
        fault_events: FaultEvents = parse_dynawo_fault_json(fault_file, source_iidm_file)
        if selected_ids is None or fault_events.name in selected_ids:
            raw_fault: object
            with fault_file.open(encoding="utf-8") as json_file:
                raw_fault = json.load(json_file)
            if not isinstance(raw_fault, dict):
                raise ValueError(f"Dynawo fault JSON must contain an object: {fault_file}")
            else:
                fault_data: dict[str, object] = raw_fault
            input_fault_type: str = require_string(fault_data, "fault_type", fault_file).lower()
            if input_fault_type in ("line", "line_fault", "linefault"):
                fault_type: str = "LineFault"
            elif input_fault_type in ("node", "node_fault", "nodefault", "transformer", "transformer_fault"):
                fault_type = "NodeFault"
            else:
                raise ValueError(f"Fault {fault_events.name}: unsupported fault type '{input_fault_type}'.")
            generated_name: str = re.sub(r"[^A-Za-z0-9_.-]", "_", fault_events.name)
            if generated_name in ("", ".", ".."):
                raise ValueError(f"Fault ID cannot be used as a folder name: {fault_events.name}")
            elif generated_name in generated_names:
                raise ValueError(f"Fault IDs map to the same output folder: {fault_events.name}")
            else:
                generated_names.add(generated_name)
            target_value: object = fault_data.get("target")
            if not isinstance(target_value, dict):
                raise ValueError(f"Fault {fault_events.name}: target must be an object.")
            else:
                target_data: dict[str, object] = target_value
            impedance_value: object = fault_data.get("impedance", dict())
            if not isinstance(impedance_value, dict):
                raise ValueError(f"Fault {fault_events.name}: impedance must be an object.")
            else:
                impedance_data: dict[str, object] = impedance_value
            terminal_2: Optional[str] = None
            distance: Optional[float] = None
            equipment_disconnections: List[tuple[str, float]] = list()
            line_trip_time: Optional[float] = None
            transformer_id: Optional[str] = None
            if fault_type == "LineFault":
                terminal_2 = require_string(target_data, "terminal_2", fault_file)
                distance = require_number(fault_data, "distance", fault_events.name)
                fault_static_id: str = require_string(target_data, "static_id", fault_file)
            else:
                fault_static_id = require_string(target_data, "static_id", fault_file)
                transformer_id_value: object = target_data.get("transformer_id")
                if transformer_id_value is not None:
                    transformer_id = require_string(target_data, "transformer_id", fault_file)
                else:
                    pass
            raw_disconnections: object = fault_data.get("disconnections")
            if raw_disconnections is None:
                raw_disconnections = derive_default_disconnections(
                    iidm_file=source_iidm_file,
                    fault_type=input_fault_type.replace("_fault", ""),
                    target_data=target_data,
                    disconnection_time=require_number(fault_data, "disconnection_time", fault_events.name),
                )
            elif not isinstance(raw_disconnections, list):
                raise ValueError(f"Fault {fault_events.name}: disconnections must be a list.")
            else:
                pass
            for raw_disconnection in raw_disconnections:
                if not isinstance(raw_disconnection, dict):
                    raise ValueError(f"Fault {fault_events.name}: each disconnection must be an object.")
                else:
                    disconnection_data: dict[str, object] = raw_disconnection
                static_id_value: object = disconnection_data.get("static_id")
                if static_id_value is not None:
                    static_id: str = require_string(disconnection_data, "static_id", fault_file)
                    if fault_type == "LineFault" and static_id == fault_static_id:
                        line_trip_time = require_number(disconnection_data, "time", fault_events.name)
                    elif transformer_id is not None and static_id == transformer_id:
                        equipment_disconnections.append((static_id, require_number(disconnection_data, "time", fault_events.name)))
                    elif static_id != fault_static_id:
                        trip_time: float = require_number(disconnection_data, "time", fault_events.name)
                        equipment_disconnections.append((static_id, trip_time))
                    else:
                        pass
                else:
                    target_line_matches: bool = False
                    if fault_type == "LineFault":
                        disconnected_first_bus: object = disconnection_data.get("first_bus")
                        disconnected_second_bus: object = disconnection_data.get("second_bus")
                        target_first_bus: object = target_data.get("first_bus")
                        target_second_bus: object = target_data.get("second_bus")
                        target_parallel_id: object = target_data.get("parallel_id")
                        disconnection_parallel_id: object = disconnection_data.get("parallel_id")
                        target_line_matches = (
                            (disconnected_first_bus == target_first_bus and disconnected_second_bus == target_second_bus)
                            or (disconnected_first_bus == target_second_bus and disconnected_second_bus == target_first_bus)
                        ) and disconnection_parallel_id == target_parallel_id
                    else:
                        pass
                    if not target_line_matches:
                        raise ValueError(
                            f"Fault {fault_events.name}: every additional disconnection needs its IIDM static_id."
                        )
                    else:
                        line_trip_time = require_number(disconnection_data, "time", fault_events.name)
            if transformer_id is not None and not any(item[0] == transformer_id for item in equipment_disconnections):
                equipment_disconnections.append((transformer_id, require_number(fault_data, "end_time", fault_events.name)))
            else:
                pass
            parsed_faults.append(
                DynawoFaultEventDescription(
                    scenario_id=generated_name,
                    fault_type=fault_type,
                    static_id=fault_static_id,
                    terminal_1=require_string(target_data, "terminal_1", fault_file),
                    terminal_2=terminal_2,
                    resistance=require_number(impedance_data, "r", fault_events.name, 0.0),
                    reactance=require_number(impedance_data, "x", fault_events.name, 0.0),
                    begin_time=require_number(fault_data, "start_time", fault_events.name),
                    end_time=require_number(fault_data, "end_time", fault_events.name),
                    distance_to_terminal_1=distance,
                    equipment_disconnections=equipment_disconnections,
                    line_trip_time=line_trip_time,
                )
            )
        else:
            pass

    if len(parsed_faults) == 0:
        raise ValueError("No fault JSON files matched the selected fault IDs.")
    else:
        pass

    if use_multiple_jobs:
        if not line_fault_model_available and any(fault.fault_type == "LineFault" for fault in parsed_faults):
            raise ValueError("Dynawo multiple jobs share one IIDM; use isolated cases for line-fault fallback.")
        else:
            pass
        multiple_case_dir: Path = case_output_dir / "multiple"
        if multiple_case_dir.exists():
            raise ValueError(f"Dynawo multiple case already exists: {multiple_case_dir}")
        else:
            pass
        shutil.copytree(source_dir, multiple_case_dir, ignore=shutil.ignore_patterns("outputs", "output"))
        scenario_files: List[DynawoPatchedScenarioFiles] = list()
        for fault_description in parsed_faults:
            if fault_description.fault_type == "NodeFault":
                enable_dynawo_bus_fault(multiple_case_dir / source_jobs.name, fault_description.terminal_1)
            else:
                pass
            dyd_file: Path = multiple_case_dir / f"{source_jobs.stem}_{fault_description.scenario_id}.dyd"
            par_file: Path = multiple_case_dir / f"{source_jobs.stem}_{fault_description.scenario_id}.par"
            write_xml_tree(
                build_scenario_dyd_tree(fault_description, generated_par_file_name=par_file.name), dyd_file
            )
            write_xml_tree(build_scenario_par_tree(fault_description), par_file)
            scenario_files.append(
                DynawoPatchedScenarioFiles(fault_description.scenario_id, dyd_file, par_file)
            )
        multiple_file: Path = multiple_case_dir / f"{source_jobs.stem}.multiple"
        write_xml_tree(build_multiple_jobs_tree(source_jobs.name, scenario_files), multiple_file)
        return [str(multiple_case_dir)]
    else:
        pass

    for fault_description in parsed_faults:
        fault_dir: Path = case_output_dir / fault_description.scenario_id
        if fault_dir.exists():
            raise ValueError(f"Dynawo output case already exists: {fault_dir}")
        else:
            pass
        shutil.copytree(source_dir, fault_dir, ignore=shutil.ignore_patterns("outputs", "output"))
        if fault_description.fault_type == "LineFault" and not line_fault_model_available:
            copied_iidm_file: Optional[Path] = None
            copied_jobs_root: ET.Element = ET.parse(fault_dir / source_jobs.name).getroot()
            for jobs_element in copied_jobs_root.iter():
                iidm_reference: Optional[str] = jobs_element.get("iidmFile")
                if iidm_reference is not None:
                    copied_iidm_file = (fault_dir / iidm_reference).resolve()
                else:
                    pass
            if copied_iidm_file is None:
                raise ValueError(f"Could not resolve the copied IIDM file for {fault_description.scenario_id}.")
            else:
                pass
            split_line_ids: tuple[str, str] = split_iidm_line_at_fault(copied_iidm_file, fault_description)
            fault_description.equipment_disconnections.extend(
                [(split_line_ids[0], fault_description.line_trip_time), (split_line_ids[1], fault_description.line_trip_time)]
            )
            fault_description.fault_type = "NodeFault"
            fault_description.static_id = f"FICT_BUS_{re.sub(r'[^A-Za-z0-9_]', '_', fault_description.scenario_id)}"
            fault_description.terminal_1 = fault_description.static_id
            fault_description.terminal_2 = None
            fault_description.distance_to_terminal_1 = None
        else:
            pass
        if fault_description.fault_type == "NodeFault":
            enable_dynawo_bus_fault(fault_dir / source_jobs.name, fault_description.terminal_1)
        else:
            pass
        copied_dyd_file: Path = fault_dir / source_dyd_file.relative_to(source_dir)
        copied_dyd_tree: ET.ElementTree = ET.parse(copied_dyd_file)
        copied_dyd_root: ET.Element = copied_dyd_tree.getroot()
        scenario_dyd_root: ET.Element = build_scenario_dyd_tree(
            fault_description,
            generated_par_file_name=f"fault_{fault_description.scenario_id}.par",
        ).getroot()
        existing_model_ids: set[str] = set()
        for model_element in copied_dyd_root.iter():
            model_id: Optional[str] = model_element.get("id")
            if model_id is not None:
                existing_model_ids.add(model_id)
            else:
                pass
        for scenario_element in scenario_dyd_root:
            scenario_model_id: Optional[str] = scenario_element.get("id")
            if scenario_model_id is not None and scenario_model_id in existing_model_ids:
                raise ValueError(
                    f"Fault {fault_description.scenario_id}: generated model ID already exists: {scenario_model_id}"
                )
            else:
                pass
        for scenario_element in list(scenario_dyd_root):
            copied_dyd_root.append(scenario_element)
        indent_xml(copied_dyd_root)
        copied_dyd_tree.write(copied_dyd_file, encoding="UTF-8", xml_declaration=True)

        generated_par_file: Path = copied_dyd_file.parent / f"fault_{fault_description.scenario_id}.par"
        generated_par_tree: ET.ElementTree = build_scenario_par_tree(fault_description)
        generated_par_tree.write(generated_par_file, encoding="UTF-8", xml_declaration=True)
        generated_folders.append(str(fault_dir))

    return generated_folders


def enable_dynawo_bus_fault(jobs_file: Path, bus_id: str) -> None:
    """Enable current terminals on a copied Dynawo network bus.

    :param jobs_file: Copied Dynawo jobs file.
    :param bus_id: Fictitious IIDM bus identifier.
    :return: None.
    """
    jobs_root: ET.Element = ET.parse(jobs_file).getroot()
    networks: list[ET.Element] = [element for element in jobs_root.iter()
                                  if element.tag.rsplit("}", 1)[-1] == "network"]
    if len(networks) != 1:
        raise ValueError(f"Expected one network in {jobs_file}.")
    else:
        pass
    par_file: Optional[str] = networks[0].get("parFile")
    par_id: Optional[str] = networks[0].get("parId")
    if par_file is None or par_id is None:
        raise ValueError(f"Network parameters are missing in {jobs_file}.")
    else:
        pass
    par_path: Path = (jobs_file.parent / par_file).resolve()
    if not par_path.is_relative_to(jobs_file.parent.resolve()):
        raise ValueError(f"Network parameter file is outside the copied case: {par_file}")
    else:
        pass
    par_tree: ET.ElementTree = ET.parse(par_path)
    par_root: ET.Element = par_tree.getroot()
    parameter_sets: list[ET.Element] = [element for element in par_root
                                        if element.tag.rsplit("}", 1)[-1] == "set" and element.get("id") == par_id]
    if len(parameter_sets) != 1:
        raise ValueError(f"Network parameter set {par_id} not found in {par_path}.")
    else:
        pass
    name: str = f"{bus_id}_hasShortCircuitCapabilities"
    found: bool = False
    for parameter in parameter_sets[0]:
        if parameter.get("name") == name:
            parameter.set("type", "BOOL")
            parameter.set("value", "true")
            found = True
        else:
            pass
    if not found:
        namespace: str = par_root.tag.split("}", 1)[0] + "}" if par_root.tag.startswith("{") else ""
        ET.SubElement(parameter_sets[0], f"{namespace}par", {"type": "BOOL", "name": name, "value": "true"})
    else:
        pass
    write_xml_tree(par_tree, par_path)


def split_iidm_line_at_fault(
    iidm_file: Path,
    fault_description: DynawoFaultEventDescription,
) -> tuple[str, str]:
    """Replace one IIDM line by two impedance-scaled segments and a fault bus.

    :param iidm_file: Copied IIDM input to modify for this scenario only.
    :param fault_description: Line fault whose static ID and distance identify
        the segment and the split point.
    :return: Static IDs of the two generated line segments.
    :raises ValueError: If the line or required bus-breaker data is unavailable.
    """
    iidm_tree: ET.ElementTree = ET.parse(iidm_file)
    iidm_root: ET.Element = iidm_tree.getroot()
    iidm_namespace: str = iidm_root.tag[1:].split("}", 1)[0]
    voltage_levels: dict[str, ET.Element] = dict()
    voltage_level_substations: dict[str, ET.Element] = dict()
    for substation in iidm_root.iter():
        if substation.tag.rsplit("}", 1)[-1] == "substation":
            for voltage_level in substation:
                if voltage_level.tag.rsplit("}", 1)[-1] == "voltageLevel":
                    voltage_level_id: Optional[str] = voltage_level.get("id")
                    if voltage_level_id is not None:
                        voltage_levels[voltage_level_id] = voltage_level
                        voltage_level_substations[voltage_level_id] = substation
                    else:
                        pass
                else:
                    pass
        else:
            pass

    fault_line: Optional[ET.Element] = None
    fault_line_parent: Optional[ET.Element] = None
    for parent in iidm_root.iter():
        for candidate in parent:
            if candidate.tag.rsplit("}", 1)[-1] == "line" and candidate.get("id") == fault_description.static_id:
                fault_line = candidate
                fault_line_parent = parent
            else:
                pass
    if fault_line is None or fault_line_parent is None:
        raise ValueError(f"Fault line is missing from copied IIDM: {fault_description.static_id}")
    else:
        pass
    voltage_level_1_id: Optional[str] = fault_line.get("voltageLevelId1")
    voltage_level_2_id: Optional[str] = fault_line.get("voltageLevelId2")
    if voltage_level_1_id is None or voltage_level_2_id is None:
        raise ValueError(f"Line {fault_description.static_id} lacks terminal voltage levels.")
    elif voltage_level_1_id not in voltage_levels or voltage_level_2_id not in voltage_levels:
        raise ValueError(f"Line {fault_description.static_id} references unknown voltage levels.")
    else:
        pass

    fault_distance: Optional[float] = fault_description.distance_to_terminal_1
    if fault_distance is None or fault_distance <= 0.0 or fault_distance >= 1.0:
        raise ValueError(f"Line {fault_description.scenario_id} needs an internal fault position between 0 and 1.")
    else:
        pass
    normalized_id: str = re.sub(r"[^A-Za-z0-9_]", "_", fault_description.scenario_id)
    fictitious_substation_id: str = f"FICT_SS_{normalized_id}"
    fictitious_voltage_level_id: str = f"FICT_VL_{normalized_id}"
    fictitious_bus_id: str = f"FICT_BUS_{normalized_id}"
    line_1_id: str = f"FICT_LINE_{normalized_id}_1"
    line_2_id: str = f"FICT_LINE_{normalized_id}_2"
    for element in iidm_root.iter():
        existing_id: Optional[str] = element.get("id")
        if existing_id in (fictitious_substation_id, fictitious_voltage_level_id, fictitious_bus_id, line_1_id, line_2_id):
            raise ValueError(f"Generated IIDM identifier already exists: {existing_id}")
        else:
            pass

    nominal_voltage: Optional[str] = voltage_levels[voltage_level_1_id].get("nominalV")
    if nominal_voltage is None:
        raise ValueError(f"Voltage level {voltage_level_1_id} has no nominal voltage.")
    else:
        pass
    first_substation: ET.Element = voltage_level_substations[voltage_level_1_id]
    country: Optional[str] = first_substation.get("country")
    if country is None:
        raise ValueError(f"Substation for voltage level {voltage_level_1_id} has no country code.")
    else:
        pass

    substation_tag: str = f"{{{iidm_namespace}}}substation"
    voltage_level_tag: str = f"{{{iidm_namespace}}}voltageLevel"
    topology_tag: str = f"{{{iidm_namespace}}}busBreakerTopology"
    bus_tag: str = f"{{{iidm_namespace}}}bus"
    fictitious_substation: ET.Element = ET.Element(substation_tag, {"id": fictitious_substation_id, "country": country})
    fictitious_voltage_level: ET.Element = ET.SubElement(
        fictitious_substation,
        voltage_level_tag,
        {"id": fictitious_voltage_level_id, "nominalV": nominal_voltage, "topologyKind": "BUS_BREAKER"},
    )
    topology: ET.Element = ET.SubElement(fictitious_voltage_level, topology_tag)
    ET.SubElement(topology, bus_tag, {"id": fictitious_bus_id})
    insert_index: int = len(iidm_root)
    for child_index, child in enumerate(iidm_root):
        if child.tag.rsplit("}", 1)[-1] != "substation":
            insert_index = child_index
            break
        else:
            pass
    iidm_root.insert(insert_index, fictitious_substation)

    line_tag: str = fault_line.tag
    line_1: ET.Element = ET.Element(line_tag, fault_line.attrib)
    line_2: ET.Element = ET.Element(line_tag, fault_line.attrib)
    line_1.set("id", line_1_id)
    line_2.set("id", line_2_id)
    line_1.set("name", line_1_id)
    line_2.set("name", line_2_id)
    source_resistance: float = float(fault_line.get("r", "0"))
    source_reactance: float = float(fault_line.get("x", "0"))
    line_1.set("r", format(source_resistance * fault_distance, ".12g"))
    line_1.set("x", format(source_reactance * fault_distance, ".12g"))
    line_2.set("r", format(source_resistance * (1.0 - fault_distance), ".12g"))
    line_2.set("x", format(source_reactance * (1.0 - fault_distance), ".12g"))
    for parameter_name in ("g1", "b1", "g2", "b2"):
        parameter_value: Optional[str] = fault_line.get(parameter_name)
        if parameter_value is not None:
            original_value: float = float(parameter_value)
            line_1.set(parameter_name, format(original_value * fault_distance, ".12g"))
            line_2.set(parameter_name, format(original_value * (1.0 - fault_distance), ".12g"))
        else:
            pass
    for load_flow_name in ("p1", "q1", "p2", "q2"):
        line_1.attrib.pop(load_flow_name, None)
        line_2.attrib.pop(load_flow_name, None)
    for suffix in ("1", "2"):
        for endpoint_attribute in ("bus", "connectableBus", "voltageLevelId", "node"):
            line_1.attrib.pop(f"{endpoint_attribute}{suffix}", None)
            line_2.attrib.pop(f"{endpoint_attribute}{suffix}", None)
    for endpoint_attribute in ("bus", "connectableBus", "node"):
        first_endpoint: Optional[str] = fault_line.get(f"{endpoint_attribute}1")
        second_endpoint: Optional[str] = fault_line.get(f"{endpoint_attribute}2")
        if first_endpoint is not None:
            line_1.set(f"{endpoint_attribute}1", first_endpoint)
            line_2.set(f"{endpoint_attribute}2", second_endpoint if second_endpoint is not None else "")
        else:
            pass
    line_1.set("voltageLevelId1", voltage_level_1_id)
    line_1.set("voltageLevelId2", fictitious_voltage_level_id)
    line_2.set("voltageLevelId1", fictitious_voltage_level_id)
    line_2.set("voltageLevelId2", voltage_level_2_id)
    line_1.set("bus2", fictitious_bus_id)
    line_1.set("connectableBus2", fictitious_bus_id)
    line_2.set("bus1", fictitious_bus_id)
    line_2.set("connectableBus1", fictitious_bus_id)
    fault_line_parent.remove(fault_line)
    fault_line_parent.append(line_1)
    fault_line_parent.append(line_2)
    # Dynawo expects the IIDM namespace as the default, even though XML permits prefixes.
    iidm_xml: str = ET.tostring(iidm_root, encoding="unicode")
    root_prefix: Optional[re.Match[str]] = re.match(r"<([\w.-]+):network\b", iidm_xml)
    if root_prefix is not None:
        prefix: str = root_prefix.group(1)
        iidm_xml = iidm_xml.replace(f"<{prefix}:", "<").replace(f"</{prefix}:", "</")
        iidm_xml = iidm_xml.replace(f'xmlns:{prefix}="{iidm_namespace}"',
                                    f'xmlns="{iidm_namespace}" xmlns:{prefix}="{iidm_namespace}"', 1)
    else:
        pass
    iidm_file.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + iidm_xml, encoding="utf-8")
    return line_1_id, line_2_id


def resolve_fault_files(fault_files: Sequence[str] | str) -> List[str]:
    """Resolve one fault file, a fault directory, or an explicit file list.

    :param fault_files: Single path, directory path, or sequence of paths.
    :return: Ordered paths to JSON fault descriptions.
    :raises ValueError: If the directory contains no JSON files or a supplied
        path does not exist.
    """
    if isinstance(fault_files, str):
        source_path: Path = Path(fault_files)
        if source_path.is_dir():
            resolved_files: List[str] = [str(path) for path in sorted(source_path.glob("*.json"))]
        elif source_path.is_file():
            resolved_files = [str(source_path)]
        else:
            raise ValueError(f"Dynawo fault path does not exist: {source_path}")
    else:
        resolved_files = list(fault_files)
        for resolved_file in resolved_files:
            if not Path(resolved_file).is_file():
                raise ValueError(f"Dynawo fault file does not exist: {resolved_file}")
            else:
                pass
    if len(resolved_files) == 0:
        raise ValueError("No Dynawo fault JSON files were found.")
    else:
        return resolved_files


def validate_case_file_references(root: ET.Element, base_dir: Path, source_name: str) -> None:
    """Ensure file references are local and will still resolve after copying.

    :param root: Parsed JOBS or DYD XML root.
    :param base_dir: Directory against which its file paths are resolved.
    :param source_name: File type included in validation errors.
    :return: Return value.
    :raises ValueError: If a required referenced file is missing or external.
    """
    for element in root.iter():
        for attribute_name, attribute_value in element.attrib.items():
            if (
                attribute_name.lower() in ("iidmfile", "dydfile", "parfile", "inputfile")
                and attribute_value.strip() != ""
            ):
                reference: Path = Path(attribute_value)
                resolved_reference: Path = (base_dir / reference).resolve()
                if reference.is_absolute() or base_dir.resolve() not in resolved_reference.parents:
                    raise ValueError(f"{source_name} references a file outside the case folder: {attribute_value}")
                elif not resolved_reference.is_file():
                    raise ValueError(f"{source_name} references a missing file: {attribute_value}")
                else:
                    pass
            else:
                pass


def require_string(data: dict[str, object], key: str, context: object) -> str:
    """Return a required non-empty string from input data.

    :param data: Parsed JSON object.
    :param key: Required key.
    :param context: Fault identifier or source path for error messages.
    :return: Required string value.
    :raises ValueError: If the key is absent or is not a non-empty string.
    """
    value: object = data.get(key)
    if isinstance(value, str) and value.strip() != "":
        return value
    else:
        raise ValueError(f"{context}: required field '{key}' must be a non-empty string.")


def require_number(
    data: dict[str, object],
    key: str,
    context: object,
    default_value: Optional[float] = None,
) -> float:
    """Return a required finite numeric value, or the supplied default.

    :param data: Parsed JSON object.
    :param key: Numeric field name.
    :param context: Fault identifier or source path for error messages.
    :param default_value: Value to use when the field is absent.
    :return: Numeric field value.
    :raises ValueError: If the value is absent without a default or invalid.
    """
    value: object = data.get(key, default_value)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context}: field '{key}' must be numeric.")
    else:
        numeric_value: float = float(value)
    if numeric_value != numeric_value or numeric_value in (float("inf"), float("-inf")):
        raise ValueError(f"{context}: field '{key}' must be finite.")
    else:
        return numeric_value
