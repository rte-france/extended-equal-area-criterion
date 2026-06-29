"""
Dynawo coupling helpers for EEAC post-processing.

:module: coupling
"""
# Copyright (c) 2020-2026, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from __future__ import annotations

import json
import os
import re
from enum import Enum
from typing import Dict, List, Optional, Sequence, Set, Tuple
from xml.etree import ElementTree as ET

import pypowsybl as pp

from deeac.DynawoPostProcess.runner import DynawoBinaryOptions, DynawoRunner
from deeac.IO.arguments_parser import DynawoRunConfiguration
from deeac.IO.dynawo.dynawo_parser import DynawoCaseFiles, DynawoJobParser, extract_branch_parallel_id, normalize_iidm_bus_name
from deeac.Models.events.branch_event import BranchEvent
from deeac.Models.events.fault_events import FaultEvents
from deeac.Models.events.line_short_circuit_clearing_event import LineShortCircuitClearingEvent
from deeac.Models.events.line_short_circuit_event import LineShortCircuitEvent
from deeac.IO.dynawo.parse_dynawo import parse_dynawo_configuration
from deeac.Simulations.results import EEACResult, EEACResults
from deeac.enums import OMIBStabilityState


class DynawoCaseGenerationStatus(Enum):
    """
    Status of an individual generated Dynawo case.

    Rationale:
        The generation stage must explicitly track success and skip reasons per
        fault so that GUI and scripts can explain what was generated and why.

    :cvar GENERATED: Case was generated.
    :cvar SKIPPED: Case was not generated.
    """

    GENERATED = "GENERATED"
    SKIPPED = "SKIPPED"


class DynawoExecutionStatus(Enum):
    """
    Execution status of an individual Dynawo run.

    Rationale:
        Dynawo runs are external process calls. This enum keeps the execution
        state explicit for machine and human reporting.

    :cvar SUCCESS: Process exited with code 0.
    :cvar FAILED: Process exited with a non-zero code.
    """

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class DynawoFaultSelectionOptions:
    """
    Selection options for filtering EEAC faults before Dynawo generation.

    Rationale:
        Customers usually want only a subset of contingencies. Selection based
        on stability status and CCT bounds keeps the policy explicit.

    :ivar statuses: Allowed stability states.
    :ivar status_names: Allowed raw EEAC status names.
    :ivar cct_min: Optional minimum CCT in seconds.
    :ivar cct_max: Optional maximum CCT in seconds.
    """

    __slots__ = ("statuses", "status_names", "cct_min", "cct_max")

    def __init__(
        self,
        statuses: Sequence[OMIBStabilityState],
        status_names: Optional[Sequence[str]] = None,
        cct_min: Optional[float] = None,
        cct_max: Optional[float] = None,
    ) -> None:
        """
        Initialize fault-selection options.

        :param statuses: Allowed stability states.
        :param status_names: Allowed raw EEAC status names.
        :param cct_min: Optional minimum CCT in seconds.
        :param cct_max: Optional maximum CCT in seconds.
        :return: Return value.
        """
        self.statuses: Set[OMIBStabilityState] = set(statuses)
        self.status_names: Set[str] = set()
        for status in statuses:
            self.status_names.add(status.value)
        if status_names is None:
            pass
        else:
            for status_name in status_names:
                self.status_names.add(status_name)
        self.cct_min: Optional[float] = cct_min
        self.cct_max: Optional[float] = cct_max


class DynawoGenerationEntry:
    """
    Generation result for one fault.

    Rationale:
        A per-fault record is easier to inspect than free-form logs and is
        designed to be directly serializable in a manifest.

    :ivar fault_name: Fault identifier from EEAC/Dynawo.
    :ivar generation_status: Generation outcome.
    :ivar reason: Human-readable reason for skip/failure.
    :ivar jobs_file: Generated jobs file path when available.
    :ivar dyd_file: Generated DYD file path when available.
    :ivar par_file: Generated PAR file path when available.
    :ivar output_dir: Dynawo output directory for this case.
    """

    __slots__ = (
        "fault_name",
        "generation_status",
        "reason",
        "jobs_file",
        "dyd_file",
        "par_file",
        "output_dir",
    )

    def __init__(
        self,
        fault_name: str,
        generation_status: DynawoCaseGenerationStatus,
        reason: Optional[str],
        jobs_file: Optional[str],
        dyd_file: Optional[str],
        par_file: Optional[str],
        output_dir: Optional[str],
    ) -> None:
        """
        Initialize the entry.

        :param fault_name: Fault identifier from EEAC/Dynawo.
        :param generation_status: Generation outcome.
        :param reason: Human-readable reason for skip/failure.
        :param jobs_file: Generated jobs file path when available.
        :param dyd_file: Generated DYD file path when available.
        :param par_file: Generated PAR file path when available.
        :param output_dir: Dynawo output directory for this case.
        :return: Return value.
        """
        self.fault_name = fault_name
        self.generation_status = generation_status
        self.reason = reason
        self.jobs_file = jobs_file
        self.dyd_file = dyd_file
        self.par_file = par_file
        self.output_dir = output_dir

    def to_dict(self) -> Dict[str, Optional[str]]:
        """
        Convert this entry to a JSON-serializable dictionary.

        :return: Serialized entry.
        """
        data: Dict[str, Optional[str]] = dict()
        data["fault_name"] = self.fault_name
        data["generation_status"] = self.generation_status.value
        data["reason"] = self.reason
        data["jobs_file"] = self.jobs_file
        data["dyd_file"] = self.dyd_file
        data["par_file"] = self.par_file
        data["output_dir"] = self.output_dir
        return data


class DynawoRunEntry:
    """
    Execution result for one generated Dynawo case.

    Rationale:
        External process calls need explicit capture of return code and streams
        to keep failures inspectable in GUI or scripted workflows.

    :ivar fault_name: Fault identifier.
    :ivar execution_status: Run status.
    :ivar return_code: Process return code.
    :ivar stdout: Captured process stdout.
    :ivar stderr: Captured process stderr.
    """

    __slots__ = ("fault_name", "execution_status", "return_code", "stdout", "stderr")

    def __init__(
        self,
        fault_name: str,
        execution_status: DynawoExecutionStatus,
        return_code: int,
        stdout: str,
        stderr: str,
    ) -> None:
        """
        Initialize the run entry.

        :param fault_name: Fault identifier.
        :param execution_status: Run status.
        :param return_code: Process return code.
        :param stdout: Captured process stdout.
        :param stderr: Captured process stderr.
        :return: Return value.
        """
        self.fault_name = fault_name
        self.execution_status = execution_status
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr

    def to_dict(self) -> Dict[str, object]:
        """
        Convert this entry to a JSON-serializable dictionary.

        :return: Serialized entry.
        """
        data: Dict[str, object] = dict()
        data["fault_name"] = self.fault_name
        data["execution_status"] = self.execution_status.value
        data["return_code"] = self.return_code
        data["stdout"] = self.stdout
        data["stderr"] = self.stderr
        return data


class DynawoCouplingReport:
    """
    Report for Dynawo case generation.

    Rationale:
        A stable report object makes it easy to persist generation state and
        consume it in the GUI integration phase.

    :ivar entries: Per-fault generation records.
    """

    __slots__ = ("entries",)

    def __init__(self, entries: Sequence[DynawoGenerationEntry]) -> None:
        """
        Initialize the report.

        :param entries: Per-fault generation records.
        :return: Return value.
        """
        self.entries: List[DynawoGenerationEntry] = list(entries)

    def to_dict(self) -> Dict[str, List[Dict[str, Optional[str]]]]:
        """
        Convert the report to a JSON-serializable dictionary.

        :return: Serialized report.
        """
        items: List[Dict[str, Optional[str]]] = list()
        for entry in self.entries:
            items.append(entry.to_dict())
        data: Dict[str, List[Dict[str, Optional[str]]]] = dict()
        data["entries"] = items
        return data


class DynawoRunReport:
    """
    Report for Dynawo execution.

    Rationale:
        Run reporting mirrors generation reporting so users can inspect process
        outcomes with minimal ambiguity.

    :ivar entries: Per-fault execution records.
    """

    __slots__ = ("entries",)

    def __init__(self, entries: Sequence[DynawoRunEntry]) -> None:
        """
        Initialize the report.

        :param entries: Per-fault execution records.
        :return: Return value.
        """
        self.entries: List[DynawoRunEntry] = list(entries)

    def to_dict(self) -> Dict[str, List[Dict[str, object]]]:
        """
        Convert the report to a JSON-serializable dictionary.

        :return: Serialized report.
        """
        items: List[Dict[str, object]] = list()
        for entry in self.entries:
            items.append(entry.to_dict())
        data: Dict[str, List[Dict[str, object]]] = dict()
        data["entries"] = items
        return data


class DynawoLineMatch:
    """
    Internal mapping record between DEEAC line events and IIDM lines.

    Rationale:
        DYD generation requires static line id and terminal ids from IIDM.

    :ivar static_id: IIDM line identifier.
    :ivar first_terminal: Terminal id for the event first bus.
    :ivar second_terminal: Terminal id for the event second bus.
    """

    __slots__ = ("static_id", "first_terminal", "second_terminal")

    def __init__(self, static_id: str, first_terminal: str, second_terminal: str) -> None:
        """
        Initialize the mapping record.

        :param static_id: IIDM line identifier.
        :param first_terminal: Terminal id for the event first bus.
        :param second_terminal: Terminal id for the event second bus.
        :return: Return value.
        """
        self.static_id = static_id
        self.first_terminal = first_terminal
        self.second_terminal = second_terminal


class DynawoCaseCoupler:
    """
    Coupler between EEAC results and Dynawo case file generation.

    Rationale:
        This class centralizes the workflow required to:
        1) filter faults from ``EEACResults``,
        2) map selected faults to Dynawo events,
        3) generate per-fault Dynawo files,
        4) optionally execute Dynawo.

    :ivar _run_configuration: Source Dynawo run configuration.
    :ivar _eeac_results: EEAC results used for filtering.
    :ivar _selection_options: Fault selection policy.
    :ivar _case_files: Resolved Dynawo base files.
    :ivar _fault_events: Parsed Dynawo fault bundles from the base case.
    """

    __slots__ = ("_run_configuration", "_eeac_results", "_selection_options", "_case_files", "_fault_events")

    def __init__(
        self,
        run_configuration: DynawoRunConfiguration,
        eeac_results: EEACResults,
        selection_options: DynawoFaultSelectionOptions,
    ) -> None:
        """
        Initialize the coupler.

        :param run_configuration: Source Dynawo run configuration.
        :param eeac_results: EEAC results used for filtering.
        :param selection_options: Fault selection policy.
        :return: Return value.
        """
        self._run_configuration = run_configuration
        self._eeac_results = eeac_results
        self._selection_options = selection_options
        self._case_files = self._resolve_case_files(run_configuration)
        self._fault_events = self._load_fault_events(run_configuration)

    def generate_cases(self, generation_root_dir: str, rewrite: bool = True) -> DynawoCouplingReport:
        """
        Generate per-fault Dynawo case files from selected EEAC results.

        :param generation_root_dir: Root directory where generated cases are stored.
        :param rewrite: Rewrite generation directory when it already exists.
        :return: Generation report with one entry per candidate fault.
        """
        self._prepare_directory(generation_root_dir, rewrite)

        entries: List[DynawoGenerationEntry] = list()
        selected_fault_names: List[str] = self._select_fault_names(self._eeac_results, self._selection_options)
        fault_lookup: Dict[str, FaultEvents] = self.build_fault_lookup(self._fault_events)
        line_lookup: Dict[str, DynawoLineMatch] = self._build_line_lookup(self._case_files.iidm_file)

        for fault_name in selected_fault_names:
            # Each selected fault is processed independently so partial generation is possible.
            fault_event_bundle: Optional[FaultEvents] = fault_lookup.get(fault_name, None)
            if fault_event_bundle is None:
                entry = DynawoGenerationEntry(
                    fault_name=fault_name,
                    generation_status=DynawoCaseGenerationStatus.SKIPPED,
                    reason="Fault selected in EEAC results but not found in Dynawo fault events.",
                    jobs_file=None,
                    dyd_file=None,
                    par_file=None,
                    output_dir=None,
                )
                entries.append(entry)
            else:
                generated_entry = self._generate_single_case(
                    generation_root_dir=generation_root_dir,
                    fault_name=fault_name,
                    fault_event_bundle=fault_event_bundle,
                    line_lookup=line_lookup,
                )
                entries.append(generated_entry)

        return DynawoCouplingReport(entries)

    def run_generated_cases(
        self,
        generation_report: DynawoCouplingReport,
        dynawo_binary_path: Optional[str] = None,
        dynawo_install_dir: Optional[str] = None,
        dynawo_binary_options: Optional[DynawoBinaryOptions] = None,
        timeout_seconds: Optional[float] = None,
    ) -> DynawoRunReport:
        """
        Run Dynawo on generated case files.

        :param generation_report: Previously generated case report.
        :param dynawo_binary_path: Optional explicit path to the Dynawo executable.
        :param dynawo_install_dir: Optional Dynawo install directory.
        :param dynawo_binary_options: Optional binary-resolution options used
            when ``dynawo_binary_path`` is not provided.
        :param timeout_seconds: Optional process timeout in seconds.
        :return: Run report with one entry per generated case.
        """
        entries: List[DynawoRunEntry] = list()
        try:
            dynawo_runner = DynawoRunner(
                dynawo_binary_path=dynawo_binary_path,
                dynawo_install_dir=dynawo_install_dir,
                dynawo_binary_options=dynawo_binary_options,
            )
        except ValueError as value_error:
            for generation_entry in generation_report.entries:
                if generation_entry.generation_status == DynawoCaseGenerationStatus.GENERATED:
                    failure_entry = DynawoRunEntry(
                        fault_name=generation_entry.fault_name,
                        execution_status=DynawoExecutionStatus.FAILED,
                        return_code=-1,
                        stdout="",
                        stderr=f"Dynawo runner initialization failed: {value_error}",
                    )
                    entries.append(failure_entry)
                else:
                    pass
            return DynawoRunReport(entries)

        for generation_entry in generation_report.entries:
            if generation_entry.generation_status == DynawoCaseGenerationStatus.GENERATED:
                if generation_entry.jobs_file is not None:
                    process_result = dynawo_runner.run_jobs_file(
                        jobs_file=generation_entry.jobs_file,
                        timeout_seconds=timeout_seconds,
                    )
                    execution_status: DynawoExecutionStatus
                    if process_result.return_code == 0:
                        execution_status = DynawoExecutionStatus.SUCCESS
                    else:
                        execution_status = DynawoExecutionStatus.FAILED
                    run_entry = DynawoRunEntry(
                        fault_name=generation_entry.fault_name,
                        execution_status=execution_status,
                        return_code=process_result.return_code,
                        stdout=process_result.stdout,
                        stderr=process_result.stderr,
                    )
                    entries.append(run_entry)
                else:
                    run_entry = DynawoRunEntry(
                        fault_name=generation_entry.fault_name,
                        execution_status=DynawoExecutionStatus.FAILED,
                        return_code=-1,
                        stdout="",
                        stderr="Generated case has no jobs file path.",
                    )
                    entries.append(run_entry)
            else:
                pass
        return DynawoRunReport(entries)

    def write_generation_manifest(self, report: DynawoCouplingReport, manifest_path: str) -> None:
        """
        Persist generation report as JSON.

        :param report: Generation report.
        :param manifest_path: Output JSON file path.
        :return: Return value.
        """
        parent_dir: str = os.path.dirname(manifest_path)
        if parent_dir == "":
            pass
        else:
            os.makedirs(parent_dir, exist_ok=True)
        json.dump(report.to_dict(), open(manifest_path, "w"), indent=2)

    def write_run_manifest(self, report: DynawoRunReport, manifest_path: str) -> None:
        """
        Persist run report as JSON.

        :param report: Run report.
        :param manifest_path: Output JSON file path.
        :return: Return value.
        """
        parent_dir: str = os.path.dirname(manifest_path)
        if parent_dir == "":
            pass
        else:
            os.makedirs(parent_dir, exist_ok=True)
        json.dump(report.to_dict(), open(manifest_path, "w"), indent=2)

    def _generate_single_case(
        self,
        generation_root_dir: str,
        fault_name: str,
        fault_event_bundle: FaultEvents,
        line_lookup: Dict[str, DynawoLineMatch],
    ) -> DynawoGenerationEntry:
        """
        Generate one Dynawo case from one fault bundle.

        :param generation_root_dir: Root generation directory.
        :param fault_name: Fault name.
        :param fault_event_bundle: Fault event bundle.
        :param line_lookup: Mapping from normalized key to IIDM line data.
        :return: Generation entry.
        """
        line_fault_event: Optional[LineShortCircuitEvent] = self._extract_line_fault_event(fault_event_bundle)
        if line_fault_event is None:
            entry = DynawoGenerationEntry(
                fault_name=fault_name,
                generation_status=DynawoCaseGenerationStatus.SKIPPED,
                reason="Fault is not a supported single line-fault event.",
                jobs_file=None,
                dyd_file=None,
                par_file=None,
                output_dir=None,
            )
            return entry
        else:
            pass

        line_lookup_key: str = self._build_line_lookup_key(
            line_fault_event.first_bus_name,
            line_fault_event.second_bus_name,
            line_fault_event.parallel_id,
        )
        line_match: Optional[DynawoLineMatch] = line_lookup.get(line_lookup_key, None)
        if line_match is None:
            entry = DynawoGenerationEntry(
                fault_name=fault_name,
                generation_status=DynawoCaseGenerationStatus.SKIPPED,
                reason="Could not map line fault to an IIDM line.",
                jobs_file=None,
                dyd_file=None,
                par_file=None,
                output_dir=None,
            )
            return entry
        else:
            pass

        fault_dir_name: str = sanitize_file_label(fault_name)
        case_dir: str = os.path.join(generation_root_dir, fault_dir_name)
        os.makedirs(case_dir, exist_ok=True)

        file_stem: str = "fault_case"
        par_path: str = os.path.join(case_dir, f"{file_stem}.par")
        dyd_path: str = os.path.join(case_dir, f"{file_stem}.dyd")
        jobs_path: str = os.path.join(case_dir, f"{file_stem}.jobs")
        dynawo_output_dir: str = os.path.join(case_dir, "outputs")
        os.makedirs(dynawo_output_dir, exist_ok=True)

        mitigation_time, disconnect_line = self._extract_mitigation_data(fault_event_bundle)
        # If there is no explicit mitigation, use the fault inception time as fallback.
        if mitigation_time is None:
            mitigation_time = line_fault_event.time
        else:
            mitigation_time = mitigation_time

        self._write_fault_par_file(
            par_path=par_path,
            line_fault_event=line_fault_event,
            mitigation_time=mitigation_time,
            disconnect_line=disconnect_line,
        )
        self._write_fault_dyd_file(
            dyd_path=dyd_path,
            fault_name=fault_name,
            line_match=line_match,
            disconnect_line=disconnect_line,
        )
        self._write_fault_jobs_file(
            source_jobs_path=self._case_files.jobs_file,
            fallback_case_files=self._case_files,
            jobs_path=jobs_path,
            generated_dyd_path=dyd_path,
            dynawo_output_dir=dynawo_output_dir,
        )

        entry = DynawoGenerationEntry(
            fault_name=fault_name,
            generation_status=DynawoCaseGenerationStatus.GENERATED,
            reason=None,
            jobs_file=jobs_path,
            dyd_file=dyd_path,
            par_file=par_path,
            output_dir=dynawo_output_dir,
        )
        return entry

    def _resolve_case_files(self, run_configuration: DynawoRunConfiguration) -> DynawoCaseFiles:
        """
        Resolve Dynawo case files from run configuration.

        :param run_configuration: Dynawo run configuration.
        :return: Resolved case files.
        """
        if run_configuration.jobs_file is not None:
            return DynawoJobParser(run_configuration.jobs_file).parse()
        else:
            iidm_file = run_configuration.iidm_file
            dyd_file = run_configuration.dynawo_dyd_file
            par_file = run_configuration.dynawo_par_file
            if iidm_file is None:
                raise ValueError("Dynawo coupling requires iidm_file when jobs_file is not provided.")
            else:
                pass
            if dyd_file is None or par_file is None:
                raise ValueError("Dynawo coupling requires both dynawo_dyd_file and dynawo_par_file in manual mode.")
            else:
                pass
            return DynawoCaseFiles(
                jobs_file=None,
                iidm_file=iidm_file,
                dyd_file=dyd_file,
                par_file=par_file,
                solver_par_file=None,
            )

    def _load_fault_events(self, run_configuration: DynawoRunConfiguration) -> List[FaultEvents]:
        """
        Parse fault events from the Dynawo input case.

        :param run_configuration: Dynawo run configuration.
        :return: Parsed fault event bundles.
        """
        network = parse_dynawo_configuration(run_configuration)
        return list(network.fault_events)

    def _select_fault_names(
        self,
        eeac_results: EEACResults,
        selection_options: DynawoFaultSelectionOptions,
    ) -> List[str]:
        """
        Select fault names from EEAC results according to policy.

        :param eeac_results: EEAC results.
        :param selection_options: Selection policy.
        :return: Selected fault names.
        """
        selected: List[str] = list()
        for fault_result in eeac_results.results:
            status_name = fault_result.result.status
            if status_name in selection_options.status_names:
                status_match = True
            else:
                status_match = False
            if status_match:
                cct_match = matches_cct_filter(
                    result=fault_result.result,
                    cct_min=selection_options.cct_min,
                    cct_max=selection_options.cct_max,
                )
                if cct_match:
                    selected.append(fault_result.fault_name)
                else:
                    pass
            else:
                pass
        return selected

    @staticmethod
    def build_fault_lookup(fault_events: Sequence[FaultEvents]) -> Dict[str, FaultEvents]:
        """
        Build lookup from fault name to fault event bundle.

        :param fault_events: Fault bundles.
        :return: Name-based lookup.
        """
        lookup: Dict[str, FaultEvents] = dict()
        for index, fault_event_bundle in enumerate(fault_events):
            # We keep an index fallback to avoid silently dropping unnamed faults.
            if fault_event_bundle.name is None:
                key: str = f"fault_{index + 1}"
            else:
                key = fault_event_bundle.name
            lookup[key] = fault_event_bundle
        return lookup

    def _build_line_lookup(self, iidm_file: str) -> Dict[str, DynawoLineMatch]:
        """
        Build IIDM line mapping used to resolve Dynawo line static ids.

        :param iidm_file: IIDM file path.
        :return: Lookup keyed by normalized line key.
        """
        powsybl_network = pp.network.load(iidm_file)
        buses = powsybl_network.get_buses(all_attributes=True)
        lines = powsybl_network.get_lines(all_attributes=True)

        bus_names_by_id: Dict[str, str] = dict()
        for bus_id, row in buses.iterrows():
            raw_name: str = str(row["name"])
            if raw_name == "":
                normalized_name = normalize_iidm_bus_name(str(bus_id))
            else:
                normalized_name = normalize_iidm_bus_name(raw_name)
            bus_names_by_id[str(bus_id)] = normalized_name

        line_lookup: Dict[str, DynawoLineMatch] = dict()
        for line_id, row in lines.iterrows():
            line_identifier: str = str(line_id)
            bus1_id: str = str(row["bus1_id"])
            bus2_id: str = str(row["bus2_id"])
            bus1_name: str = bus_names_by_id.get(bus1_id, bus1_id)
            bus2_name: str = bus_names_by_id.get(bus2_id, bus2_id)
            parallel_id: str = extract_branch_parallel_id(line_identifier)
            key: str = self._build_line_lookup_key(bus1_name, bus2_name, parallel_id)
            line_lookup[key] = DynawoLineMatch(
                static_id=line_identifier,
                first_terminal=f"{bus1_id}_TN_ACPIN",
                second_terminal=f"{bus2_id}_TN_ACPIN",
            )
        return line_lookup

    def _extract_line_fault_event(self, fault_event_bundle: FaultEvents) -> Optional[LineShortCircuitEvent]:
        """
        Extract a supported line-fault event from a fault bundle.

        :param fault_event_bundle: Fault bundle.
        :return: Line-fault event when supported.
        """
        matching_events: List[LineShortCircuitEvent] = list()
        for failure_event in fault_event_bundle.failure_events:
            if isinstance(failure_event, LineShortCircuitEvent):
                matching_events.append(failure_event)
            else:
                pass
        if len(matching_events) == 1:
            return matching_events[0]
        else:
            return None

    def _extract_mitigation_data(self, fault_event_bundle: FaultEvents) -> Tuple[Optional[float], bool]:
        """
        Extract mitigation time and line-disconnection mode.

        :param fault_event_bundle: Fault bundle.
        :return: Tuple of mitigation time and disconnection flag.
        """
        branch_open_time: Optional[float] = None
        line_clear_time: Optional[float] = None
        has_branch_opening: bool = False

        for mitigation_event in fault_event_bundle.mitigation_events:
            if isinstance(mitigation_event, BranchEvent):
                if mitigation_event.breaker_closed:
                    pass
                else:
                    has_branch_opening = True
                    if branch_open_time is None:
                        branch_open_time = mitigation_event.time
                    else:
                        branch_open_time = min(branch_open_time, mitigation_event.time)
            else:
                if isinstance(mitigation_event, LineShortCircuitClearingEvent):
                    if line_clear_time is None:
                        line_clear_time = mitigation_event.time
                    else:
                        line_clear_time = min(line_clear_time, mitigation_event.time)
                else:
                    pass

        if has_branch_opening:
            return branch_open_time, True
        else:
            return line_clear_time, False

    def _write_fault_par_file(
        self,
        par_path: str,
        line_fault_event: LineShortCircuitEvent,
        mitigation_time: float,
        disconnect_line: bool,
    ) -> None:
        """
        Write a minimal fault PAR file.

        :param par_path: Output PAR path.
        :param line_fault_event: Source line-fault event.
        :param mitigation_time: Fault clearing/mitigation time.
        :param disconnect_line: Whether line disconnection is used.
        :return: Return value.
        """
        dynawo_xml_namespace: str = _dynawo_xml_namespace()
        ET.register_namespace("", dynawo_xml_namespace)
        root = ET.Element(f"{{{dynawo_xml_namespace}}}parametersSet")

        if disconnect_line:
            event_set = ET.SubElement(root, f"{{{dynawo_xml_namespace}}}set", {"id": "9"})
            ET.SubElement(
                event_set,
                f"{{{dynawo_xml_namespace}}}par",
                {"type": "DOUBLE", "name": "event_tEvent", "value": format_float(mitigation_time)},
            )
            ET.SubElement(
                event_set,
                f"{{{dynawo_xml_namespace}}}par",
                {"type": "BOOL", "name": "event_stateEvent1", "value": "true"},
            )
            ET.SubElement(
                event_set,
                f"{{{dynawo_xml_namespace}}}par",
                {"type": "BOOL", "name": "event_disconnectExtremity", "value": "true"},
            )
        else:
            pass

        fault_set = ET.SubElement(root, f"{{{dynawo_xml_namespace}}}set", {"id": "10"})
        ET.SubElement(
            fault_set,
            f"{{{dynawo_xml_namespace}}}par",
            {"type": "DOUBLE", "name": "line_RFaultPu", "value": format_float(line_fault_event.fault_resistance)},
        )
        ET.SubElement(
            fault_set,
            f"{{{dynawo_xml_namespace}}}par",
            {"type": "DOUBLE", "name": "line_XFaultPu", "value": format_float(line_fault_event.fault_reactance)},
        )
        ET.SubElement(
            fault_set,
            f"{{{dynawo_xml_namespace}}}par",
            {"type": "DOUBLE", "name": "line_tBegin", "value": format_float(line_fault_event.time)},
        )
        ET.SubElement(
            fault_set,
            f"{{{dynawo_xml_namespace}}}par",
            {"type": "DOUBLE", "name": "line_tEnd", "value": format_float(mitigation_time)},
        )
        ET.SubElement(
            fault_set,
            f"{{{dynawo_xml_namespace}}}par",
            {"type": "DOUBLE", "name": "line_D", "value": format_float(line_fault_event.fault_position)},
        )

        tree = ET.ElementTree(root)
        tree.write(par_path, encoding="UTF-8", xml_declaration=True)

    def _write_fault_dyd_file(
        self,
        dyd_path: str,
        fault_name: str,
        line_match: DynawoLineMatch,
        disconnect_line: bool,
    ) -> None:
        """
        Write a minimal fault DYD file.

        :param dyd_path: Output DYD path.
        :param fault_name: Fault name.
        :param line_match: IIDM line mapping.
        :param disconnect_line: Whether line disconnection is used.
        :return: Return value.
        """
        dynawo_xml_namespace: str = _dynawo_xml_namespace()
        ET.register_namespace("dyn", dynawo_xml_namespace)
        root = ET.Element(f"{{{dynawo_xml_namespace}}}dynamicModelsArchitecture")

        line_model_id: str = sanitize_identifier(fault_name)
        if disconnect_line:
            ET.SubElement(
                root,
                f"{{{dynawo_xml_namespace}}}blackBoxModel",
                {"id": "DISCONNECT_LINE", "lib": "EventConnectedStatus", "parFile": os.path.basename(dyd_path).replace(".dyd", ".par"), "parId": "9"},
            )
            ET.SubElement(
                root,
                f"{{{dynawo_xml_namespace}}}connect",
                {
                    "id1": "DISCONNECT_LINE",
                    "var1": "event_state1_value",
                    "id2": line_model_id,
                    "var2": "line_switchOffSignal1_value",
                },
            )
        else:
            pass

        ET.SubElement(
            root,
            f"{{{dynawo_xml_namespace}}}blackBoxModel",
            {
                "id": line_model_id,
                "lib": "LineFault",
                "parFile": os.path.basename(dyd_path).replace(".dyd", ".par"),
                "parId": "10",
                "staticId": line_match.static_id,
            },
        )
        ET.SubElement(
            root,
            f"{{{dynawo_xml_namespace}}}connect",
            {"id1": line_model_id, "var1": "line_terminal1", "id2": "NETWORK", "var2": line_match.first_terminal},
        )
        ET.SubElement(
            root,
            f"{{{dynawo_xml_namespace}}}connect",
            {"id1": line_model_id, "var1": "line_terminal2", "id2": "NETWORK", "var2": line_match.second_terminal},
        )

        tree = ET.ElementTree(root)
        tree.write(dyd_path, encoding="UTF-8", xml_declaration=True)

    def _write_fault_jobs_file(
        self,
        source_jobs_path: Optional[str],
        fallback_case_files: DynawoCaseFiles,
        jobs_path: str,
        generated_dyd_path: str,
        dynawo_output_dir: str,
    ) -> None:
        """
        Write a jobs file that points to the generated fault DYD and output dir.

        :param source_jobs_path: Source jobs path when available.
        :param fallback_case_files: Resolved case files for manual mode.
        :param jobs_path: Output jobs path.
        :param generated_dyd_path: Generated DYD path.
        :param dynawo_output_dir: Dynawo outputs directory for this case.
        :return: Return value.
        """
        if source_jobs_path is not None:
            source_root = ET.parse(source_jobs_path).getroot()
            jobs_tree = ET.ElementTree(source_root)
            source_jobs_dir = os.path.dirname(source_jobs_path)
            jobs_dir = os.path.dirname(jobs_path)
            generated_dyd_relpath = os.path.relpath(generated_dyd_path, jobs_dir)
            for element in source_root.iter():
                tag = strip_xml_namespace(element.tag)
                if tag == "dynModels":
                    element.set("dydFile", generated_dyd_relpath)
                else:
                    pass
                rewrite_file_attribute_if_present(
                    element=element,
                    attribute_name="iidmFile",
                    source_jobs_dir=source_jobs_dir,
                    target_jobs_dir=jobs_dir,
                )
                rewrite_file_attribute_if_present(
                    element=element,
                    attribute_name="parFile",
                    source_jobs_dir=source_jobs_dir,
                    target_jobs_dir=jobs_dir,
                )
                rewrite_file_attribute_if_present(
                    element=element,
                    attribute_name="inputFile",
                    source_jobs_dir=source_jobs_dir,
                    target_jobs_dir=jobs_dir,
                )
                if tag == "outputs":
                    element.set("directory", dynawo_output_dir)
                else:
                    pass
            jobs_tree.write(jobs_path, encoding="UTF-8", xml_declaration=True)
        else:
            jobs_root = self._build_jobs_xml_from_case_files(
                case_files=fallback_case_files,
                generated_dyd_path=generated_dyd_path,
                jobs_path=jobs_path,
                dynawo_output_dir=dynawo_output_dir,
            )
            jobs_tree = ET.ElementTree(jobs_root)
            jobs_tree.write(jobs_path, encoding="UTF-8", xml_declaration=True)

    def _build_jobs_xml_from_case_files(
        self,
        case_files: DynawoCaseFiles,
        generated_dyd_path: str,
        jobs_path: str,
        dynawo_output_dir: str,
    ) -> ET.Element:
        """
        Build a minimal jobs XML from resolved case files.

        :param case_files: Resolved case files.
        :param generated_dyd_path: Generated DYD path.
        :param jobs_path: Output jobs path.
        :param dynawo_output_dir: Dynawo output directory.
        :return: Jobs XML root.
        """
        dynawo_xml_namespace: str = _dynawo_xml_namespace()
        ET.register_namespace("dyn", dynawo_xml_namespace)
        jobs_dir = os.path.dirname(jobs_path)
        iidm_relpath = os.path.relpath(case_files.iidm_file, jobs_dir)
        if case_files.par_file is None:
            raise ValueError("Dynawo coupling requires par_file to write jobs in manual mode.")
        else:
            pass
        par_relpath = os.path.relpath(case_files.par_file, jobs_dir)
        dyd_relpath = os.path.relpath(generated_dyd_path, jobs_dir)

        root = ET.Element(f"{{{dynawo_xml_namespace}}}jobs")
        job = ET.SubElement(root, f"{{{dynawo_xml_namespace}}}job", {"name": "DEEAC generated fault case"})
        solver_attributes: Dict[str, str] = dict()
        solver_attributes["lib"] = "dynawo_SolverIDA"
        if case_files.solver_par_file is None:
            solver_attributes["parFile"] = par_relpath
            solver_attributes["parId"] = "1"
        else:
            solver_attributes["parFile"] = os.path.relpath(case_files.solver_par_file, jobs_dir)
            solver_attributes["parId"] = "1"
        ET.SubElement(job, f"{{{dynawo_xml_namespace}}}solver", solver_attributes)
        modeler = ET.SubElement(job, f"{{{dynawo_xml_namespace}}}modeler", {"compileDir": "outputs/compilation"})
        ET.SubElement(
            modeler,
            f"{{{dynawo_xml_namespace}}}network",
            {"iidmFile": iidm_relpath, "parFile": par_relpath, "parId": "1"},
        )
        ET.SubElement(modeler, f"{{{dynawo_xml_namespace}}}dynModels", {"dydFile": dyd_relpath})
        ET.SubElement(modeler, f"{{{dynawo_xml_namespace}}}precompiledModels", {"useStandardModels": "true"})
        ET.SubElement(modeler, f"{{{dynawo_xml_namespace}}}modelicaModels", {"useStandardModels": "true"})
        ET.SubElement(job, f"{{{dynawo_xml_namespace}}}simulation", {"startTime": "0", "stopTime": "15"})
        outputs = ET.SubElement(job, f"{{{dynawo_xml_namespace}}}outputs", {"directory": dynawo_output_dir})
        ET.SubElement(outputs, f"{{{dynawo_xml_namespace}}}timeline", {"exportMode": "TXT"})
        ET.SubElement(outputs, f"{{{dynawo_xml_namespace}}}logs")
        return root

    def _build_line_lookup_key(self, first_bus_name: str, second_bus_name: str, parallel_id: str) -> str:
        """
        Build a normalized lookup key for an unordered line with parallel id.

        :param first_bus_name: First bus name.
        :param second_bus_name: Second bus name.
        :param parallel_id: Parallel id.
        :return: Lookup key.
        """
        left_bus: str = normalize_iidm_bus_name(first_bus_name)
        right_bus: str = normalize_iidm_bus_name(second_bus_name)
        if left_bus <= right_bus:
            smallest = left_bus
            largest = right_bus
        else:
            smallest = right_bus
            largest = left_bus
        return f"{smallest}|{largest}|{parallel_id}"

    def _prepare_directory(self, target_dir: str, rewrite: bool) -> None:
        """
        Prepare the generation directory.

        :param target_dir: Directory to prepare.
        :param rewrite: Whether existing content can be removed.
        :return: Return value.
        """
        if os.path.isdir(target_dir):
            if rewrite:
                for child_name in os.listdir(target_dir):
                    child_path = os.path.join(target_dir, child_name)
                    if os.path.isdir(child_path):
                        for root_dir, child_dirs, child_files in os.walk(child_path, topdown=False):
                            for file_name in child_files:
                                file_path = os.path.join(root_dir, file_name)
                                os.remove(file_path)
                            for directory_name in child_dirs:
                                directory_path = os.path.join(root_dir, directory_name)
                                os.rmdir(directory_path)
                        os.rmdir(child_path)
                    else:
                        os.remove(child_path)
            else:
                raise ValueError(f"Generation directory already exists: {target_dir}")
        else:
            os.makedirs(target_dir, exist_ok=True)


def matches_cct_filter(result: EEACResult, cct_min: Optional[float], cct_max: Optional[float]) -> bool:
    """
    Check if one EEAC result matches CCT bounds.

    :param result: EEAC result.
    :param cct_min: Optional lower bound.
    :param cct_max: Optional upper bound.
    :return: True when CCT is inside bounds.
    """
    cct_value = result.cct
    if cct_min is None and cct_max is None:
        return True
    else:
        if cct_value is None:
            return False
        else:
            lower_ok: bool
            upper_ok: bool
            if cct_min is None:
                lower_ok = True
            else:
                lower_ok = cct_value >= cct_min
            if cct_max is None:
                upper_ok = True
            else:
                upper_ok = cct_value <= cct_max
            return lower_ok and upper_ok


def sanitize_identifier(raw_name: str) -> str:
    """
    Sanitize a raw string for safe Dynawo model identifiers.

    :param raw_name: Raw identifier.
    :return: Sanitized identifier.
    """
    cleaned_name = re.sub(r"[^A-Za-z0-9_]", "_", raw_name)
    if cleaned_name == "":
        return "fault"
    else:
        return cleaned_name


def sanitize_file_label(raw_name: str) -> str:
    """
    Sanitize a raw string for safe file/folder names.

    :param raw_name: Raw label.
    :return: Sanitized file-safe label.
    """
    cleaned_name = re.sub(r"[^A-Za-z0-9._-]", "_", raw_name)
    if cleaned_name == "":
        return "fault"
    else:
        return cleaned_name


def format_float(value: float) -> str:
    """
    Format a float for deterministic XML output.

    :param value: Numeric value.
    :return: Formatted string.
    """
    return f"{value:.12g}"


def strip_xml_namespace(tag: str) -> str:
    """
    Strip the namespace prefix from an XML tag.

    :param tag: XML tag.
    :return: Namespace-free tag.
    """
    return tag.split("}")[-1]


def rewrite_file_attribute_if_present(
    element: ET.Element,
    attribute_name: str,
    source_jobs_dir: str,
    target_jobs_dir: str,
) -> None:
    """
    Rewrite one file attribute from source-jobs-relative to target-jobs-relative.

    :param element: XML element.
    :param attribute_name: File attribute name.
    :param source_jobs_dir: Source jobs directory.
    :param target_jobs_dir: Target jobs directory.
    :return: Return value.
    """
    current_value: Optional[str] = element.get(attribute_name)
    if current_value is None:
        pass
    else:
        source_absolute_path: str
        if os.path.isabs(current_value):
            source_absolute_path = current_value
        else:
            source_absolute_path = os.path.abspath(os.path.join(source_jobs_dir, current_value))
        rewritten_value: str = os.path.relpath(source_absolute_path, target_jobs_dir)
        element.set(attribute_name, rewritten_value)


def _dynawo_xml_namespace() -> str:
    """
    Return the Dynawo XML namespace.

    :return: Namespace string.
    """
    return "http://www.rte-france.com/dynawo"
