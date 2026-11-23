"""
Dynawo file patching helpers.

:module: patch_files
"""
# Copyright (c) 2020-2025, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence
from xml.etree import ElementTree as ET


DYNAWO_NAMESPACE: str = "http://www.rte-france.com/dynawo"
ET.register_namespace("dyn", DYNAWO_NAMESPACE)
ET.register_namespace("", DYNAWO_NAMESPACE)


class DynawoFaultEventDescription:
    """
    Parsed Dynawo fault event description.

    :ivar scenario_id: Scenario identifier used by the multiple-jobs file.
    :ivar fault_type: Dynawo fault type.
    :ivar static_id: Dynawo static identifier of the faulted element.
    :ivar terminal_1: First network terminal.
    :ivar terminal_2: Optional second network terminal.
    :ivar resistance: Fault resistance in per-unit.
    :ivar reactance: Fault reactance in per-unit.
    :ivar begin_time: Fault application time in seconds.
    :ivar end_time: Fault clearing time in seconds.
    :ivar distance_to_terminal_1: Optional line-fault position measured from terminal 1.
    """

    __slots__ = (
        "scenario_id",
        "fault_type",
        "static_id",
        "terminal_1",
        "terminal_2",
        "resistance",
        "reactance",
        "begin_time",
        "end_time",
        "distance_to_terminal_1",
        "equipment_disconnections",
        "line_trip_time",
    )

    def __init__(
        self,
        scenario_id: str,
        fault_type: str,
        static_id: str,
        terminal_1: str,
        terminal_2: Optional[str],
        resistance: float,
        reactance: float,
        begin_time: float,
        end_time: float,
        distance_to_terminal_1: Optional[float],
        equipment_disconnections: Sequence[tuple[str, float]] = (),
        line_trip_time: Optional[float] = None,
    ) -> None:
        """
        Initialize the event description.

        :param scenario_id: Scenario identifier used by the multiple-jobs file.
        :param fault_type: Dynawo fault type.
        :param static_id: Dynawo static identifier of the faulted element.
        :param terminal_1: First network terminal.
        :param terminal_2: Optional second network terminal.
        :param resistance: Fault resistance in per-unit.
        :param reactance: Fault reactance in per-unit.
        :param begin_time: Fault application time in seconds.
        :param end_time: Fault clearing time in seconds.
        :param distance_to_terminal_1: Optional line-fault position measured from terminal 1.
        :param line_trip_time: Optional disconnection time for the faulted line.
        :return: Return value.
        """
        self.scenario_id = scenario_id
        self.fault_type = fault_type
        self.static_id = static_id
        self.terminal_1 = terminal_1
        self.terminal_2 = terminal_2
        self.resistance = resistance
        self.reactance = reactance
        self.begin_time = begin_time
        self.end_time = end_time
        self.distance_to_terminal_1 = distance_to_terminal_1
        self.equipment_disconnections = list(equipment_disconnections)
        self.line_trip_time = end_time if line_trip_time is None else line_trip_time


class DynawoPatchedScenarioFiles:
    """
    Paths of the generated Dynawo files for one scenario.

    :ivar scenario_id: Scenario identifier used by the multiple-jobs file.
    :ivar dyd_file: Generated DYD file path.
    :ivar par_file: Generated PAR file path.
    """

    __slots__ = ("scenario_id", "dyd_file", "par_file")

    def __init__(self, scenario_id: str, dyd_file: Path, par_file: Path) -> None:
        """
        Initialize generated file paths for one scenario.

        :param scenario_id: Scenario identifier used by the multiple-jobs file.
        :param dyd_file: Generated DYD file path.
        :param par_file: Generated PAR file path.
        :return: Return value.
        """
        self.scenario_id = scenario_id
        self.dyd_file = dyd_file
        self.par_file = par_file


class DynawoPatchedCaseFiles:
    """
    Paths of all generated Dynawo files for one patched case.

    :ivar scenarios: Generated files for each scenario.
    :ivar multiple_jobs_file: Generated multiple-jobs file path.
    """

    __slots__ = ("scenarios", "multiple_jobs_file")

    def __init__(self, scenarios: Sequence[DynawoPatchedScenarioFiles], multiple_jobs_file: Path) -> None:
        """
        Initialize the generated case file set.

        :param scenarios: Generated files for each scenario.
        :param multiple_jobs_file: Generated multiple-jobs file path.
        :return: Return value.
        """
        self.scenarios = list(scenarios)
        self.multiple_jobs_file = multiple_jobs_file


def parse_dynawo_fault_event_file(event_file: Path) -> DynawoFaultEventDescription:
    """
    Parse one Dynawo fault event description file.

    Rationale:
        The IEEE14 v2 Dynawo fixtures separate the network base case from the
        fault catalogue. The event XML file is therefore the source of truth
        for the fault timing, electrical parameters, and target branch
        terminals. Parsing this file into one explicit object is the first
        patching step because every generated DYD and PAR fragment is derived
        from these values.

    :param event_file: Path to the event description file.
    :return: Parsed fault event description.
    :rtype: DynawoFaultEventDescription
    """
    root: ET.Element = ET.parse(event_file).getroot()

    # The event files are flat parameter lists, so one explicit lookup per field keeps the mapping obvious.
    fault_type: str = get_required_parameter_value(root, "fault_type")
    static_id: str = get_required_parameter_value(root, "staticId")
    terminal_1: str = get_required_parameter_value(root, "terminal1")
    terminal_2: Optional[str] = get_optional_parameter_value(root, "terminal2")
    resistance: float = float(get_required_parameter_value(root, "r_fault"))
    reactance: float = float(get_required_parameter_value(root, "x_fault"))
    begin_time: float = float(get_required_parameter_value(root, "t_begin"))
    end_time: float = float(get_required_parameter_value(root, "t_end"))
    distance_to_terminal_1_value: Optional[str] = get_optional_parameter_value(root, "d_terminal1")
    distance_to_terminal_1: Optional[float] = None

    if distance_to_terminal_1_value is not None:
        distance_to_terminal_1 = float(distance_to_terminal_1_value)
    else:
        distance_to_terminal_1 = None

    return DynawoFaultEventDescription(
        scenario_id=event_file.stem,
        fault_type=fault_type,
        static_id=static_id,
        terminal_1=terminal_1,
        terminal_2=terminal_2,
        resistance=resistance,
        reactance=reactance,
        begin_time=begin_time,
        end_time=end_time,
        distance_to_terminal_1=distance_to_terminal_1,
    )


def get_required_parameter_value(root: ET.Element, parameter_name: str) -> str:
    """
    Get one required parameter value from an event description file.

    Rationale:
        The patching workflow is only meaningful if the event description is
        complete. A missing ``staticId`` or missing fault timing would produce a
        Dynawo scenario that looks syntactically valid while silently targeting
        the wrong network element or no element at all. This helper centralizes
        that hard-failure policy.

    :param root: XML root element.
    :param parameter_name: Parameter name to read.
    :return: Parameter value.
    :rtype: str
    """
    parameter_value: Optional[str] = get_optional_parameter_value(root, parameter_name)

    # Required fields define the generated Dynawo topology, so they must fail explicitly when absent.
    if parameter_value is not None:
        return parameter_value
    else:
        raise ValueError(f"Missing required event parameter: {parameter_name}")


def get_optional_parameter_value(root: ET.Element, parameter_name: str) -> Optional[str]:
    """
    Get one optional parameter value from an event description file.

    Rationale:
        Some event fields are structurally optional in the current patching
        model. For example, the fault position along a line is not needed for
        all future fault kinds even though it is present in the IEEE14 line
        fixtures. This helper keeps that distinction explicit instead of mixing
        optional and mandatory reads in the main parser.

    :param root: XML root element.
    :param parameter_name: Parameter name to read.
    :return: Parameter value when present.
    :rtype: Optional[str]
    """
    parameter_element: Optional[ET.Element] = root.find(f"./par[@name='{parameter_name}']")

    if parameter_element is not None:
        return parameter_element.get("value")
    else:
        return None


def build_scenario_dyd_tree(
    event_description: DynawoFaultEventDescription,
    generated_par_file_name: str,
) -> ET.ElementTree:
    """
    Build one generated DYD tree for a fault scenario.

    Rationale:
        Dynawo does not consume the generic event XML file directly. It expects
        the dynamic architecture to contain event models wired to the network.
        For the IEEE14 line-fault workflow that means building a dedicated DYD
        file containing two models:
        1. the line-fault model itself;
        2. a switch-off event that clears the line at fault end time.
        This function materializes that architecture from the neutral event
        description.

    :param event_description: Parsed fault event description.
    :param generated_par_file_name: File name of the generated PAR file.
    :return: Generated DYD tree.
    :rtype: ET.ElementTree
    """
    root: ET.Element = ET.Element(qualified_tag("dynamicModelsArchitecture"))
    fault_model_id: str = normalize_fault_model_id(event_description.scenario_id)

    if event_description.fault_type == "LineFault":
        disconnect_model = ET.SubElement(
            root,
            qualified_tag("blackBoxModel"),
            {"id": "DISCONNECT_LINE", "lib": "EventConnectedStatus", "parFile": generated_par_file_name, "parId": "9"},
        )
        disconnect_connect = ET.SubElement(
            root,
            qualified_tag("connect"),
            {"id1": "DISCONNECT_LINE", "var1": "event_state1_value", "id2": fault_model_id,
             "var2": "line_switchOffSignal1_value"},
        )
        disconnect_connect.tail = "\n  "
        disconnect_model.tail = "\n  "
    else:
        pass

    # The line-fault model keeps the event topology explicit and points at the generated parameter set.
    line_fault_model = ET.SubElement(
        root,
        qualified_tag("blackBoxModel"),
        {
            "id": fault_model_id,
            "lib": event_description.fault_type,
            "parFile": generated_par_file_name,
            "parId": "10",
            "staticId": event_description.static_id,
        },
    )
    line_fault_model.tail = "\n  "

    fault_terminal_variable: str = "line_terminal1"
    if event_description.fault_type == "NodeFault":
        # NodeFault connects to the network terminal directly, not an IIDM device model.
        line_fault_model.attrib.pop("staticId")
        fault_terminal_variable = "fault_terminal"
    else:
        pass
    first_terminal_connect = ET.SubElement(
        root,
        qualified_tag("connect"),
        {
            "id1": fault_model_id,
            "var1": fault_terminal_variable,
            "id2": "NETWORK",
            "var2": f"{event_description.terminal_1}_ACPIN",
        },
    )
    first_terminal_connect.tail = "\n  "

    if event_description.fault_type == "LineFault" and event_description.terminal_2 is not None:
        second_terminal_value: str = event_description.terminal_2
        second_terminal_connect = ET.SubElement(
            root,
            qualified_tag("connect"),
            {"id1": fault_model_id, "var1": "line_terminal2", "id2": "NETWORK",
             "var2": f"{second_terminal_value}_ACPIN"},
        )
        second_terminal_connect.tail = "\n  "
    elif event_description.fault_type == "LineFault":
        raise ValueError(f"Line fault {event_description.scenario_id} is missing terminal2.")
    else:
        pass

    for disconnection_index, disconnection in enumerate(event_description.equipment_disconnections):
        equipment_id: str = f"DISCONNECT_EQUIPMENT_{disconnection_index}"
        trip_parameter_id: str = f"TRIP_{disconnection_index}"
        trip_model = ET.SubElement(
            root,
            qualified_tag("blackBoxModel"),
            {"id": equipment_id, "lib": "EventQuadripoleDisconnection", "parFile": generated_par_file_name,
             "parId": trip_parameter_id},
        )
        trip_model.tail = "\n  "
        trip_connect = ET.SubElement(
            root,
            qualified_tag("connect"),
            {"id1": equipment_id, "var1": "event_state1", "id2": "NETWORK",
             "var2": f"{disconnection[0]}_state"},
        )
        trip_connect.tail = "\n  "
    else:
        pass

    indent_xml(root)
    return ET.ElementTree(root)


def build_scenario_par_tree(event_description: DynawoFaultEventDescription) -> ET.ElementTree:
    """
    Build one generated PAR tree for a fault scenario.

    Rationale:
        The generated DYD file only declares which event models exist. Dynawo
        still needs one PAR file containing the numerical values that drive the
        fault and the disconnection event. In the IEEE14 v2 pattern those values
        live in two parameter sets:
        set 9 for the disconnection event and set 10 for the line-fault model.
        This function rebuilds that minimal parameter file from the neutral
        event XML inputs.

    :param event_description: Parsed fault event description.
    :return: Generated PAR tree.
    :rtype: ET.ElementTree
    """
    root: ET.Element = ET.Element(qualified_tag("parametersSet"))

    if event_description.fault_type == "LineFault":
        disconnect_set = ET.SubElement(root, qualified_tag("set"), {"id": "9"})
        disconnect_set.text = "\n    "
        add_parameter(disconnect_set, "DOUBLE", "event_tEvent", format_float(event_description.line_trip_time))
        add_parameter(disconnect_set, "BOOL", "event_stateEvent1", "true")
        add_parameter(disconnect_set, "BOOL", "event_disconnectExtremity", "true")
        disconnect_set[-1].tail = "\n  "
        disconnect_set.tail = "\n  "
    else:
        pass

    # Set 10 carries the line-fault electrical parameters and timing.
    line_fault_set = ET.SubElement(root, qualified_tag("set"), {"id": "10"})
    line_fault_set.text = "\n    "
    if event_description.fault_type == "LineFault":
        add_parameter(line_fault_set, "DOUBLE", "line_RFaultPu", format_float(event_description.resistance))
        add_parameter(line_fault_set, "DOUBLE", "line_XFaultPu", format_float(event_description.reactance))
        add_parameter(line_fault_set, "DOUBLE", "line_tBegin", format_float(event_description.begin_time))
        add_parameter(line_fault_set, "DOUBLE", "line_tEnd", format_float(event_description.end_time))
        if event_description.distance_to_terminal_1 is not None:
            add_parameter(line_fault_set, "DOUBLE", "line_D", format_float(event_description.distance_to_terminal_1))
        else:
            pass
    else:
        add_parameter(line_fault_set, "DOUBLE", "fault_RPu", format_float(event_description.resistance))
        add_parameter(line_fault_set, "DOUBLE", "fault_XPu", format_float(event_description.reactance))
        add_parameter(line_fault_set, "DOUBLE", "fault_tBegin", format_float(event_description.begin_time))
        add_parameter(line_fault_set, "DOUBLE", "fault_tEnd", format_float(event_description.end_time))
    line_fault_set[-1].tail = "\n  "
    line_fault_set.tail = "\n"

    for disconnection_index, disconnection in enumerate(event_description.equipment_disconnections):
        trip_set = ET.SubElement(root, qualified_tag("set"), {"id": f"TRIP_{disconnection_index}"})
        trip_set.text = "\n    "
        add_parameter(trip_set, "DOUBLE", "event_tEvent", format_float(disconnection[1]))
        add_parameter(trip_set, "BOOL", "event_disconnectOrigin", "true")
        add_parameter(trip_set, "BOOL", "event_disconnectExtremity", "true")
        trip_set[-1].tail = "\n  "
        trip_set.tail = "\n  "
    else:
        pass

    indent_xml(root)
    return ET.ElementTree(root)


def build_multiple_jobs_tree(
    jobs_file_name: str,
    generated_scenarios: Sequence[DynawoPatchedScenarioFiles],
) -> ET.ElementTree:
    """
    Build the generated multiple-jobs tree for a set of scenarios.

    Rationale:
        Dynawo multi-scenario execution needs one dispatcher file that lists the
        scenario-specific DYD files while reusing the same base jobs file. The
        IEEE14 v2 fixture names this file ``IEEE14_MULTIPLE.xml``. This helper
        creates that dispatch layer so the generated per-fault DYD files can be
        launched as one Dynawo batch instead of isolated manual runs.

    :param jobs_file_name: Base Dynawo jobs file name.
    :param generated_scenarios: Generated scenario file paths.
    :return: Generated multiple-jobs tree.
    :rtype: ET.ElementTree
    """
    root: ET.Element = ET.Element(qualified_tag("multipleJobs"))
    scenarios_element = ET.SubElement(root, qualified_tag("scenarios"), {"jobsFile": jobs_file_name})
    scenarios_element.text = "\n    "

    # The scenario order follows the provided event order so callers control the final execution list explicitly.
    for generated_scenario in generated_scenarios:
        scenario_element = ET.SubElement(
            scenarios_element,
            qualified_tag("scenario"),
            {
                "id": generated_scenario.scenario_id,
                "dydFile": generated_scenario.dyd_file.name,
            },
        )
        scenario_element.tail = "\n    "

    scenarios_element[-1].tail = "\n  "
    scenarios_element.tail = "\n"

    indent_xml(root)
    return ET.ElementTree(root)


def patch_dynawo_case_for_events(
    jobs_file: Path,
    event_files: Sequence[Path],
    output_dir: Path,
) -> DynawoPatchedCaseFiles:
    """
    Generate per-fault Dynawo DYD/PAR files plus the multiple-jobs file.

    Rationale:
        This is the top-level patching entry point for the current Dynawo
        workflow. The base case stays untouched, the neutral event XML files are
        parsed, and then one runnable Dynawo scenario is generated per event.
        The result mirrors the structure described in the IEEE14 v2 ReadMe:
        dedicated DYD and PAR files for each event plus one MULTIPLE file that
        points at all generated scenarios.

    :param jobs_file: Base Dynawo jobs file.
    :param event_files: Event description files to patch into Dynawo scenarios.
    :param output_dir: Output directory receiving generated files.
    :return: Generated Dynawo case file paths.
    :rtype: DynawoPatchedCaseFiles
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_scenarios: List[DynawoPatchedScenarioFiles] = list()

    # Each event becomes one self-contained DYD/PAR pair so Dynawo can run scenarios independently.
    for event_file in event_files:
        event_description = parse_dynawo_fault_event_file(event_file)
        generated_dyd_file = output_dir / build_generated_dyd_file_name(event_description.scenario_id)
        generated_par_file = output_dir / build_generated_par_file_name(event_description.scenario_id)

        write_xml_tree(build_scenario_dyd_tree(event_description, generated_par_file.name), generated_dyd_file)
        write_xml_tree(build_scenario_par_tree(event_description), generated_par_file)
        generated_scenarios.append(
            DynawoPatchedScenarioFiles(
                scenario_id=event_description.scenario_id,
                dyd_file=generated_dyd_file,
                par_file=generated_par_file,
            )
        )

    generated_multiple_jobs_file: Path = output_dir / build_generated_multiple_jobs_file_name(jobs_file)
    write_xml_tree(build_multiple_jobs_tree(jobs_file.name, generated_scenarios), generated_multiple_jobs_file)

    return DynawoPatchedCaseFiles(
        scenarios=generated_scenarios,
        multiple_jobs_file=generated_multiple_jobs_file,
    )


def build_generated_dyd_file_name(scenario_id: str) -> str:
    """
    Build the generated DYD file name for one scenario.

    Rationale:
        The fixture convention uses one base prefix plus the scenario id to make
        generated files easy to map back to their source event. Keeping that
        naming policy centralized prevents drift between the generated DYD, PAR,
        and MULTIPLE references.

    :param scenario_id: Scenario identifier used by the multiple-jobs file.
    :return: Generated DYD file name.
    :rtype: str
    """
    return f"IEEE14_DYD_{scenario_id}.xml"


def build_generated_par_file_name(scenario_id: str) -> str:
    """
    Build the generated PAR file name for one scenario.

    Rationale:
        The generated PAR file must share the same scenario suffix as the DYD
        file because the DYD patch points to it explicitly. Using one helper for
        the naming rule prevents mismatches between written files and XML
        references.

    :param scenario_id: Scenario identifier used by the multiple-jobs file.
    :return: Generated PAR file name.
    :rtype: str
    """
    return f"IEEE14_PAR_{scenario_id}.xml"


def build_generated_multiple_jobs_file_name(jobs_file: Path) -> str:
    """
    Build the generated multiple-jobs file name.

    Rationale:
        The MULTIPLE file is conceptually derived from the base jobs file, not
        from any individual event. The fixture naming convention keeps the case
        prefix and swaps the suffix to ``MULTIPLE``. This helper isolates that
        translation so callers do not hardcode case-specific names.

    :param jobs_file: Base Dynawo jobs file.
    :return: Generated multiple-jobs file name.
    :rtype: str
    """
    jobs_stem_parts: List[str] = jobs_file.stem.split("_")

    if len(jobs_stem_parts) > 0:
        return f"{jobs_stem_parts[0]}_MULTIPLE.xml"
    else:
        return "MULTIPLE.xml"


def normalize_fault_model_id(scenario_id: str) -> str:
    """
    Normalize a scenario identifier into a Dynawo model identifier.

    Rationale:
        The event file identifiers use hyphens because they are human-facing
        scenario names, while the generated DYD fixture uses underscores in the
        black-box model id. This helper captures that fixture-specific mapping
        so the rest of the patching code can talk in terms of scenario ids.

    :param scenario_id: Scenario identifier used by the multiple-jobs file.
    :return: Dynawo model identifier.
    :rtype: str
    """
    normalized_value: str = scenario_id.replace("-", "_")

    # The IEEE14 reference fixtures keep the scenario id for external naming but
    # drop the separator between the ``Line`` prefix and the first bus number in
    # the internal DYD model id.
    if normalized_value.startswith("Line_"):
        return "Line" + normalized_value[len("Line_"):]
    else:
        return normalized_value


def qualified_tag(tag_name: str) -> str:
    """
    Build one namespaced Dynawo tag name.

    Rationale:
        All generated XML files must live in the Dynawo namespace to be
        accepted by Dynawo and to match the existing fixtures. Using one helper
        avoids sprinkling raw namespace strings across the patch builders.

    :param tag_name: Local XML tag name.
    :return: Namespaced XML tag name.
    :rtype: str
    """
    return f"{{{DYNAWO_NAMESPACE}}}{tag_name}"


def add_parameter(parent_element: ET.Element, parameter_type: str, parameter_name: str, parameter_value: str) -> None:
    """
    Add one Dynawo parameter element to a parent parameter set.

    Rationale:
        The generated PAR files are repetitive parameter lists with stable XML
        attribute structure. This helper keeps those additions uniform and makes
        the semantic intent clear: each call adds one Dynawo parameter row to a
        generated parameter set.

    :param parent_element: Parent XML element receiving the parameter.
    :param parameter_type: Dynawo parameter type.
    :param parameter_name: Dynawo parameter name.
    :param parameter_value: Dynawo parameter value.
    :return: Return value.
    """
    parameter_element = ET.SubElement(
        parent_element,
        qualified_tag("par"),
        {
            "type": parameter_type,
            "name": parameter_name,
            "value": parameter_value,
        },
    )
    parameter_element.tail = "\n    "


def write_xml_tree(xml_tree: ET.ElementTree, output_file: Path) -> None:
    """
    Write one XML tree to disk using the project XML formatting conventions.

    Rationale:
        The patching workflow is valuable only if the generated files can be
        handed straight to Dynawo and also inspected in tests or diffs. This
        helper centralizes the final write step so the module always emits XML
        declarations and creates parent folders when needed.

    :param xml_tree: XML tree to write.
    :param output_file: Output file path.
    :return: Return value.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    xml_tree.write(output_file, encoding="UTF-8", xml_declaration=True)


def indent_xml(element: ET.Element, level: int = 0) -> None:
    """
    Apply deterministic indentation to an XML element tree.

    Rationale:
        Dynawo itself mostly cares about XML structure, but humans comparing the
        generated files against fixture references care about stable formatting.
        Deterministic indentation keeps the produced DYD, PAR, and MULTIPLE
        files readable and supports exact or near-exact fixture comparisons in
        tests.

    :param element: XML element to indent recursively.
    :param level: Current indentation level.
    :return: Return value.
    """
    indent_value: str = "\n" + level * "  "
    child_indent_value: str = "\n" + (level + 1) * "  "

    # Stable indentation keeps test fixtures readable and makes exact-file diffs inspectable.
    if len(element) > 0:
        if element.text is None or element.text.strip() == "":
            element.text = child_indent_value
        else:
            element.text = element.text

        last_index: int = len(element) - 1
        child_index: int = 0
        for child_element in element:
            indent_xml(child_element, level + 1)
            if child_index == last_index:
                child_element.tail = indent_value
            else:
                child_element.tail = child_indent_value
            child_index += 1
    else:
        if element.text is None:
            element.text = None
        else:
            element.text = element.text


def format_float(value: float) -> str:
    """
    Format one floating-point value using Dynawo fixture conventions.

    Rationale:
        The IEEE14 fixture mixes integer-looking times such as ``10`` with
        fractional values such as ``10.1``. The generated files should preserve
        that compact style because it matches the reference artifacts and keeps
        patch diffs focused on semantics rather than float noise.

    :param value: Floating-point value to format.
    :return: Formatted value.
    :rtype: str
    """
    # General formatting preserves integers as ``10`` while still keeping short decimal values such as ``10.1``.
    return f"{value:g}"
