"""
Dynawo parsing helpers.

:module: dynawo_parser
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

import os
from typing import Dict, Iterable, List, Optional, Sequence, Set
from xml.etree import ElementTree as ET

import math
from collections import defaultdict

import pypowsybl as pp
from deeac.Models.bus import Bus
from deeac.Models.capacitor_bank import CapacitorBank
from deeac.Models.events.breaker_event import BreakerEvent
from deeac.Models.events.bus_short_circuit_clearing_event import BusShortCircuitClearingEvent
from deeac.Models.events.bus_short_circuit_event import BusShortCircuitEvent
from deeac.Models.events.mitigation_event import MitigationEvent
from deeac.Models.generator import Generator, GeneratorType
from deeac.Models.load import Load
from deeac.Models.line import Line
from deeac.Models.transformer import Transformer
from deeac.Models.events.fault_events import FaultEvents
from deeac.Models.events.branch_event import BranchEvent
from deeac.Models.events.line_short_circuit_clearing_event import LineShortCircuitClearingEvent
from deeac.Models.events.line_short_circuit_event import LineShortCircuitEvent
from deeac.Models.network import Network
from deeac.enums import BreakerPosition, GeneratorSource, parse_generator_source


class DynawoCaseFiles:
    """
    Resolved Dynawo case file set.
    
    Rationale:
        Dynawo cases are naturally described by a `.jobs` file which then
        points to the IIDM, DYD, PAR, and solver files. This class stores the
        resolved file paths used by the Dynawo workflow.
    
    :ivar jobs_file: Path to the Dynawo `.jobs` file when available.
    :ivar iidm_file: Path to the IIDM network file.
    :ivar dyd_file: Path to the Dynawo `.dyd` file.
    :ivar par_file: Path to the Dynawo `.par` file.
    :ivar solver_par_file: Optional solver parameter file from `.jobs`.
    """

    __slots__ = ("jobs_file", "iidm_file", "dyd_file", "par_file", "solver_par_file")

    def __init__(
            self,
            jobs_file: Optional[str],
            iidm_file: str,
            dyd_file: Optional[str],
            par_file: Optional[str],
            solver_par_file: Optional[str],
    ) -> None:
        """
        Initialize the resolved Dynawo case file set.
        
        :param jobs_file: Path to the Dynawo `.jobs` file when available.
        :param iidm_file: Path to the IIDM network file.
        :param dyd_file: Path to the Dynawo `.dyd` file.
        :param par_file: Path to the Dynawo `.par` file.
        :param solver_par_file: Optional solver parameter file from `.jobs`.
        :return: Return value.
        """
        self.jobs_file = jobs_file
        self.iidm_file = iidm_file
        self.dyd_file = dyd_file
        self.par_file = par_file
        self.solver_par_file = solver_par_file


class DynawoBlackBoxModel:
    """
    Dynawo black-box model definition extracted from `.dyd`.
    
    Rationale:
        Dynawo event and dynamic models are declared as black-box models in the
        `.dyd` architecture. This class stores the subset of fields needed by
        DEEAC to map dynamic models and supported fault models.
    
    :ivar model_id: Internal Dynawo model identifier.
    :ivar library_name: Dynawo library name.
    :ivar par_id: Parameter set identifier in the `.par` file.
    :ivar static_id: Optional IIDM static identifier.
    """

    __slots__ = ("model_id", "library_name", "par_id", "static_id")

    def __init__(
            self,
            model_id: str,
            library_name: str,
            par_id: Optional[str],
            static_id: Optional[str],
    ) -> None:
        """
        Initialize the model definition.
        
        :param model_id: Internal Dynawo model identifier.
        :param library_name: Dynawo library name.
        :param par_id: Parameter set identifier in the `.par` file.
        :param static_id: Optional IIDM static identifier.
        :return: Return value.
        """
        self.model_id = model_id
        self.library_name = library_name
        self.par_id = par_id
        self.static_id = static_id


class DynawoConnect:
    """
    Dynawo model connection extracted from `.dyd`.
    
    Rationale:
        Some event end-times are not stored directly on the fault model but are
        driven by another event model connected through the Dynawo wiring. This
        class stores those explicit links.
    
    :ivar source_id: Source model identifier.
    :ivar source_variable: Source variable name.
    :ivar target_id: Target model identifier.
    :ivar target_variable: Target variable name.
    """

    __slots__ = ("source_id", "source_variable", "target_id", "target_variable")

    def __init__(
            self,
            source_id: str,
            source_variable: str,
            target_id: str,
            target_variable: str,
    ) -> None:
        """
        Initialize the connection.
        
        :param source_id: Source model identifier.
        :param source_variable: Source variable name.
        :param target_id: Target model identifier.
        :param target_variable: Target variable name.
        :return: Return value.
        """
        self.source_id = source_id
        self.source_variable = source_variable
        self.target_id = target_id
        self.target_variable = target_variable


class DynawoJobParser:
    """
    Dynawo `.jobs` parser.
    
    Rationale:
        The `.jobs` file is the natural entrypoint for a Dynawo case because it
        references the IIDM network, the DYD architecture, the PAR file, and
        the solver parameters in one place. This parser resolves those paths.
    
    :ivar jobs_file: Path to the Dynawo `.jobs` file.
    """

    __slots__ = ("jobs_file",)

    def __init__(self, jobs_file: str) -> None:
        """
        Initialize the `.jobs` parser.
        
        :param jobs_file: Path to the Dynawo `.jobs` file.
        :return: Return value.
        """
        self.jobs_file = jobs_file

    def parse(self) -> DynawoCaseFiles:
        """
        Parse the `.jobs` file and resolve the core Dynawo file paths.
        
        :return: Resolved Dynawo case files.
        :raise ValueError: If the expected Dynawo file references are missing.
        """
        root: ET.Element = ET.parse(self.jobs_file).getroot()
        base_dir: str = os.path.dirname(self.jobs_file)

        iidm_file: Optional[str] = None
        dyd_file: Optional[str] = None
        par_file: Optional[str] = None
        solver_par_file: Optional[str] = None

        for element in root.iter():
            tag_name: str = strip_namespace(element.tag)
            if tag_name == "network":
                iidm_name: Optional[str] = element.get("iidmFile")
                par_name: Optional[str] = element.get("parFile")
                if iidm_name is not None:
                    iidm_file = resolve_dynawo_path(base_dir, iidm_name)
                else:
                    iidm_file = iidm_file
                if par_name is not None:
                    par_file = resolve_dynawo_path(base_dir, par_name)
                else:
                    par_file = par_file
            elif tag_name == "dynModels":
                dyd_name: Optional[str] = element.get("dydFile")
                if dyd_name is not None:
                    dyd_file = resolve_dynawo_path(base_dir, dyd_name)
                else:
                    dyd_file = dyd_file
            elif tag_name == "solver":
                solver_name: Optional[str] = element.get("parFile")
                if solver_name is not None:
                    solver_par_file = resolve_dynawo_path(base_dir, solver_name)
                else:
                    solver_par_file = solver_par_file
            else:
                pass

        if iidm_file is None:
            raise ValueError(f"No IIDM network file found in Dynawo jobs file {self.jobs_file}")
        if dyd_file is None:
            raise ValueError(f"No DYD file found in Dynawo jobs file {self.jobs_file}")
        if par_file is None:
            raise ValueError(f"No PAR file found in Dynawo jobs file {self.jobs_file}")

        return DynawoCaseFiles(
            jobs_file=self.jobs_file,
            iidm_file=iidm_file,
            dyd_file=dyd_file,
            par_file=par_file,
            solver_par_file=solver_par_file,
        )


class DynawoGeneratorParameters:
    """
    Dynawo generator parameters loaded from .par.
    
    Rationale:
        This class holds the generator parameters extracted from Dynawo inputs,
        which are then used to populate dynamic parameters on the Network model.
    
    :ivar inertia_constant: Inertia constant (H) in seconds on the machine base.
    :ivar direct_transient_reactance_pu: Direct transient reactance (X'd) in per-unit.
    :ivar rated_apparent_power: Generator nominal apparent power in MVA.
    :ivar machine_side_voltage: Generator machine-side voltage base in kV.
    """

    __slots__ = (
        "inertia_constant",
        "direct_transient_reactance_pu",
        "rated_apparent_power",
        "machine_side_voltage",
    )

    def __init__(
            self,
            inertia_constant: Optional[float],
            direct_transient_reactance_pu: Optional[float],
            rated_apparent_power: Optional[float],
            machine_side_voltage: Optional[float],
    ) -> None:
        """
        Initialize the Dynawo generator parameters.

        :param inertia_constant: Inertia constant (H) in seconds.
        :param direct_transient_reactance_pu: Direct transient reactance (X'd) in per-unit.
        :param rated_apparent_power: Generator nominal apparent power in MVA.
        :param machine_side_voltage: Generator machine-side voltage base in kV.
        :return: Return value.
        """
        self.inertia_constant = inertia_constant
        self.direct_transient_reactance_pu = direct_transient_reactance_pu
        self.rated_apparent_power = rated_apparent_power
        self.machine_side_voltage = machine_side_voltage


class DynawoData:
    """
    Parsed Dynawo data.
    
    Rationale:
        This class aggregates Dynawo parameters in a structured mapping keyed by
        the IIDM staticId used by the Dynawo .dyd file.
    
    :ivar generator_params_by_id: Mapping from IIDM staticId to generator parameters.
    """

    def __init__(self, generator_params_by_id: Dict[str, DynawoGeneratorParameters]) -> None:
        """
        Initialize the parsed Dynawo data container.
        
        :param generator_params_by_id: Mapping from IIDM staticId to generator parameters.
        :return: Return value.
        """
        self.generator_params_by_id = dict(generator_params_by_id)

    def get_generator_parameters(self, static_id: str) -> Optional[DynawoGeneratorParameters]:
        """
        Get Dynawo parameters for a generator staticId.
        
        :param static_id: IIDM generator identifier.
        :return: Dynawo generator parameters if found.
        """
        return self.generator_params_by_id.get(static_id)

    def has_dynamic_generator(self, static_id: str) -> bool:
        """
        Tell whether a generator has usable machine dynamics.

        :param static_id: IIDM generator identifier.
        :return: ``True`` when the generator has positive inertia and transient reactance.
        """
        params = self.get_generator_parameters(static_id)
        if params is None:
            return False
        if params.inertia_constant is None or params.inertia_constant <= 0:
            return False
        if params.direct_transient_reactance_pu is None or params.direct_transient_reactance_pu <= 0:
            return False
        return True


class DynawoParametersParser:
    """
    Dynawo .dyd/.par parameter parser.

    Rationale:
        Dynawo stores dynamic parameters in .par and binds them to IIDM static
        elements via .dyd. This parser extracts the parameters needed to
        populate generator dynamics inside the Network model.

    :ivar dyd_file: Path to the Dynawo .dyd file.
    :ivar par_file: Path to the Dynawo .par file.
    """

    def __init__(self, dyd_file: Optional[str], par_file: Optional[str]) -> None:
        """
        Initialize the Dynawo parameter parser.

        :param dyd_file: Path to the Dynawo .dyd file.
        :param par_file: Path to the Dynawo .par file.
        :return: Return value.
        """
        self.dyd_file = dyd_file
        self.par_file = par_file

    def parse(self) -> DynawoData:
        """
        Parse Dynawo files into a generator-parameter mapping.

        :return: Parsed Dynawo data.
        """
        if not self._has_inputs():
            return DynawoData({})
        if not (os.path.exists(self.dyd_file) and os.path.exists(self.par_file)):
            return DynawoData({})

        static_id_to_par_id = self._parse_dyd(self.dyd_file)
        par_sets = self.parse_par(self.par_file)

        generator_params: Dict[str, DynawoGeneratorParameters] = {}
        for static_id, par_id in static_id_to_par_id.items():
            params = par_sets.get(par_id)
            if params is None:
                continue
            inertia = self._get_float(params, "generator_H")
            xpd = self._get_float(params, "generator_XpdPu")
            rated_apparent_power = self._get_float(params, "generator_SNom")
            machine_side_voltage = self._get_float(params, "generator_UBaseLV")
            if machine_side_voltage is None:
                machine_side_voltage = self._get_float(params, "generator_UNomLV")
            else:
                machine_side_voltage = machine_side_voltage
            if machine_side_voltage is None:
                machine_side_voltage = self._get_float(params, "generator_UNom")
            else:
                machine_side_voltage = machine_side_voltage
            if xpd is None:
                xpd = self._get_float(params, "generator_XdPu")
            else:
                xpd = xpd
            if inertia is None and xpd is None:
                continue
            generator_params[static_id] = DynawoGeneratorParameters(
                inertia_constant=inertia,
                direct_transient_reactance_pu=xpd,
                rated_apparent_power=rated_apparent_power,
                machine_side_voltage=machine_side_voltage,
            )

        return DynawoData(generator_params)

    def _has_inputs(self) -> bool:
        """
        Check if both Dynawo files were provided.

        :return: True when both files are available.
        """
        return bool(self.dyd_file and self.par_file)

    def _parse_dyd(self, file_path: str) -> Dict[str, str]:
        """
        Parse the .dyd file and map staticId to parId.

        :param file_path: Path to the .dyd file.
        :return: Mapping from staticId to parId.
        """
        root = self._read_xml(file_path)
        mapping: Dict[str, str] = {}
        for model in self._iter_by_tag(root, "blackBoxModel"):
            static_id = model.get("staticId")
            par_id = model.get("parId")
            if static_id and par_id:
                mapping[static_id] = par_id
        return mapping

    def parse_par(self, file_path: str) -> Dict[str, Dict[str, object]]:
        """
        Parse the .par file and map parameter set ids to parameter dictionaries.

        :param file_path: Path to the .par file.
        :return: Mapping from set id to parameter name/value dictionary.
        """
        root = self._read_xml(file_path)
        sets: Dict[str, Dict[str, object]] = {}
        for param_set in self._iter_by_tag(root, "set"):
            set_id = param_set.get("id")
            if not set_id:
                continue
            params: Dict[str, object] = {}
            for par in self._iter_by_tag(param_set, "par"):
                name = par.get("name")
                if not name:
                    continue
                value = self._parse_value(par.get("value"), par.get("type"))
                params[name] = value
            sets[set_id] = params
        return sets

    def _read_xml(self, file_path: str) -> ET.Element:
        """
        Read an XML file and return its root element.

        :param file_path: Path to the XML file.
        :return: Root XML element.
        """
        return ET.parse(file_path).getroot()

    def _iter_by_tag(self, root: ET.Element, tag_name: str) -> Iterable[ET.Element]:
        """
        Yield elements matching a tag name, ignoring namespaces.

        :param root: XML root element.
        :param tag_name: Tag name to match.
        :return: Iterator over matching elements.
        """
        for element in root.iter():
            if element.tag.split("}")[-1] == tag_name:
                yield element

    def _parse_value(self, raw_value: Optional[str], raw_type: Optional[str]) -> Optional[object]:
        """
        Parse a Dynawo parameter value.

        :param raw_value: Raw string value.
        :param raw_type: Dynawo type name.
        :return: Parsed value.
        """
        if raw_value is None:
            return None
        if raw_type is None:
            return raw_value
        type_name = raw_type.upper()
        if type_name == "DOUBLE":
            try:
                return float(raw_value)
            except ValueError:
                return None
        if type_name == "INT":
            try:
                return int(raw_value)
            except ValueError:
                return None
        if type_name == "BOOL":
            return raw_value.lower() == "true"
        return raw_value

    def _get_float(self, params: Dict[str, object], name: str) -> Optional[float]:
        """
        Get a float parameter value.

        :param params: Parameter dictionary.
        :param name: Parameter name.
        :return: Parsed float value if present.
        """
        value = params.get(name)
        if isinstance(value, (int, float)):
            return float(value)
        else:
            return None


class DynawoMultiFileParser:
    """
    Dynawo multi-file case parser.
    
    Rationale:
        This parser is the Dynawo-side equivalent of the Eurostag workflow. It
        resolves a Dynawo case, loads the IIDM network, augments generator
        parameters from `.dyd` and `.par`, and builds supported fault events
        from the Dynawo dynamic architecture.
    
    :ivar jobs_file: Optional Dynawo `.jobs` file.
    :ivar iidm_file: Optional IIDM file path used in manual mode.
    :ivar dyd_file: Optional DYD file path used in manual mode.
    :ivar par_file: Optional PAR file path used in manual mode.
    """

    __slots__ = (
        "jobs_file",
        "iidm_file",
        "dyd_file",
        "par_file",
        "dotted_generator_inertia_multiplier",
    )

    def __init__(
            self,
            jobs_file: Optional[str],
            iidm_file: Optional[str],
            dyd_file: Optional[str],
            par_file: Optional[str],
            dotted_generator_inertia_multiplier: float = 1.0,
    ) -> None:
        """
        Initialize the Dynawo multi-file parser.
        
        :param jobs_file: Optional Dynawo `.jobs` file.
        :param iidm_file: Optional IIDM file path used in manual mode.
        :param dyd_file: Optional DYD file path used in manual mode.
        :param par_file: Optional PAR file path used in manual mode.
        :param dotted_generator_inertia_multiplier: Multiplier applied during
            Dynawo parsing to generators whose IIDM id starts with ``.``.
        :return: Return value.
        """
        self.jobs_file = jobs_file
        self.iidm_file = iidm_file
        self.dyd_file = dyd_file
        self.par_file = par_file
        self.dotted_generator_inertia_multiplier = dotted_generator_inertia_multiplier

    def parse(self) -> Network:
        """
        Parse a Dynawo case into a DEEAC network with fault events.
        
        :return: Parsed network.
        """
        case_files: DynawoCaseFiles = self._resolve_case_files()

        parser: IidmParser = IidmParser(
            fname=case_files.iidm_file,
            dynawo_dyd_file=case_files.dyd_file,
            dynawo_par_file=case_files.par_file,
            dotted_generator_inertia_multiplier=self.dotted_generator_inertia_multiplier,
        )
        network: Network = parser.parse()
        fault_events: List[FaultEvents] = self._parse_fault_events(case_files)
        network.set_fault_events(fault_events)
        return network

    def _resolve_case_files(self) -> DynawoCaseFiles:
        """
        Resolve the files used by the Dynawo case.
        
        :return: Resolved Dynawo case files.
        :raise ValueError: If the file set is incomplete.
        """
        if self.jobs_file is not None:
            return DynawoJobParser(self.jobs_file).parse()
        else:
            if self.iidm_file is None:
                raise ValueError("Dynawo workflow requires either jobs_file or iidm_file.")
            if (self.dyd_file is None) ^ (self.par_file is None):
                raise ValueError("Dynawo workflow requires both dyd_file and par_file together.")
            return DynawoCaseFiles(
                jobs_file=None,
                iidm_file=self.iidm_file,
                dyd_file=self.dyd_file,
                par_file=self.par_file,
                solver_par_file=None,
            )

    def _parse_fault_events(self, case_files: DynawoCaseFiles) -> List[FaultEvents]:
        """
        Parse supported Dynawo fault events.
        
        :param case_files: Resolved Dynawo case files.
        :return: Parsed fault event bundles.
        """
        if case_files.dyd_file is None or case_files.par_file is None:
            return list()
        models: Dict[str, DynawoBlackBoxModel] = parse_dyd_models(case_files.dyd_file)
        connects: List[DynawoConnect] = parse_dyd_connects(case_files.dyd_file)
        parameter_sets: Dict[str, Dict[str, object]] = DynawoParametersParser(
            case_files.dyd_file,
            case_files.par_file,
        ).parse_par(case_files.par_file)
        return build_dynawo_fault_events(case_files.iidm_file, models, connects, parameter_sets)


def strip_namespace(tag: str) -> str:
    """
    Strip the XML namespace from a tag name.
    
    :param tag: XML tag.
    :return: Namespace-free tag.
    """
    return tag.split("}")[-1]


def normalize_iidm_bus_name(bus_name: str) -> str:
    """
    Normalize an IIDM bus name to the DEEAC naming used by Eurostag cases.

    PowSybl exposes solved bus names such as ``BUS    1_VL_0`` for bus-breaker
    topologies. DEEAC, Eurostag inputs, and the private regression cases use
    the simpler bus naming ``BUS    1``. Normalizing here keeps Dynawo and
    Eurostag cases aligned.

    :param bus_name: Raw IIDM bus name.
    :return: Normalized bus name.
    """
    if bus_name.endswith("_VL_0"):
        return bus_name[:-5]
    else:
        return bus_name


def extract_branch_parallel_id(branch_id: str) -> str:
    """
    Extract the DEEAC branch parallel identifier from an IIDM branch id.

    Dynawo IIDM branch identifiers usually end with ``-<parallel>_AC`` for
    lines or ``-<parallel>_PT`` for transformers. DEEAC stores that parallel
    index separately on the branch.

    :param branch_id: IIDM branch identifier.
    :return: Branch parallel identifier.
    """
    branch_body: str
    if branch_id.endswith("_AC"):
        branch_body = branch_id[:-3]
    elif branch_id.endswith("_PT"):
        branch_body = branch_id[:-3]
    else:
        branch_body = branch_id

    branch_parts: List[str] = branch_body.rsplit("-", 1)
    if len(branch_parts) == 2:
        return branch_parts[1]
    else:
        return branch_body


def resolve_dynawo_path(base_dir: str, file_name: str) -> str:
    """
    Resolve a path from a Dynawo file relative to its parent directory.
    
    :param base_dir: Base directory of the referencing file.
    :param file_name: Raw relative or absolute file path.
    :return: Resolved path.
    """
    if os.path.isabs(file_name):
        return file_name
    else:
        return os.path.join(base_dir, file_name)


def parse_dyd_models(dyd_file: str) -> Dict[str, DynawoBlackBoxModel]:
    """
    Parse black-box model definitions from a Dynawo `.dyd` file.
    
    :param dyd_file: Path to the Dynawo `.dyd` file.
    :return: Model definitions keyed by Dynawo model id.
    """
    root: ET.Element = ET.parse(dyd_file).getroot()
    models: Dict[str, DynawoBlackBoxModel] = dict()
    for element in root.iter():
        tag_name: str = strip_namespace(element.tag)
        if tag_name == "blackBoxModel":
            model_id: Optional[str] = element.get("id")
            library_name: Optional[str] = element.get("lib")
            if model_id is not None and library_name is not None:
                models[model_id] = DynawoBlackBoxModel(
                    model_id=model_id,
                    library_name=library_name,
                    par_id=element.get("parId"),
                    static_id=element.get("staticId"),
                )
            else:
                pass
        else:
            pass
    return models


def parse_dyd_connects(dyd_file: str) -> List[DynawoConnect]:
    """
    Parse model connections from a Dynawo `.dyd` file.
    
    :param dyd_file: Path to the Dynawo `.dyd` file.
    :return: Parsed connection list.
    """
    root: ET.Element = ET.parse(dyd_file).getroot()
    connects: List[DynawoConnect] = list()
    for element in root.iter():
        tag_name: str = strip_namespace(element.tag)
        if tag_name == "connect":
            source_id: Optional[str] = element.get("id1")
            source_variable: Optional[str] = element.get("var1")
            target_id: Optional[str] = element.get("id2")
            target_variable: Optional[str] = element.get("var2")
            if (
                    source_id is not None and
                    source_variable is not None and
                    target_id is not None and
                    target_variable is not None
            ):
                connects.append(
                    DynawoConnect(
                        source_id=source_id,
                        source_variable=source_variable,
                        target_id=target_id,
                        target_variable=target_variable,
                    )
                )
            else:
                pass
        else:
            pass
    return connects


def build_dynawo_fault_events(
        iidm_file: str,
        models: Dict[str, DynawoBlackBoxModel],
        connects: List[DynawoConnect],
        parameter_sets: Dict[str, Dict[str, object]],
) -> List[FaultEvents]:
    """
    Build supported Dynawo fault events from the model and parameter data.
    
    :param iidm_file: Path to the IIDM file used for static-id resolution.
    :param models: Dynawo model definitions.
    :param connects: Dynawo model connections.
    :param parameter_sets: Dynawo `.par` sets keyed by id.
    :return: Parsed fault event bundles.
    """
    network_lines = load_iidm_line_data(iidm_file)
    fault_events: List[FaultEvents] = list()

    for model in models.values():
        library_name: str = model.library_name.lower()
        if library_name == "linefault":
            line_fault_events: Optional[FaultEvents] = build_line_fault_events(
                model,
                models,
                connects,
                parameter_sets,
                network_lines,
            )
            if line_fault_events is not None:
                fault_events.append(line_fault_events)
            else:
                pass
        else:
            pass

    return fault_events


def load_iidm_line_data(iidm_file: str) -> Dict[str, Dict[str, str]]:
    """
    Load IIDM line data needed to map Dynawo static ids to bus names.
    
    :param iidm_file: Path to the IIDM file.
    :return: Mapping from IIDM line id to bus-name pairs.
    """
    powsybl_network = pp.network.load(iidm_file)
    buses = powsybl_network.get_buses(all_attributes=True)
    lines = powsybl_network.get_lines(all_attributes=True)

    bus_names_by_id: Dict[str, str] = dict()
    for bus_id, row in buses.iterrows():
        bus_name = row["name"]
        if bus_name == "":
            bus_names_by_id[str(bus_id)] = str(bus_id)
        else:
            bus_names_by_id[str(bus_id)] = normalize_iidm_bus_name(str(bus_name))

    line_data: Dict[str, Dict[str, str]] = dict()
    for line_id, row in lines.iterrows():
        if row["connected1"] and row["connected2"]:
            first_bus_id: str = str(row["bus1_id"])
            second_bus_id: str = str(row["bus2_id"])
            line_data[str(line_id)] = {
                "first_bus_name": bus_names_by_id[first_bus_id],
                "second_bus_name": bus_names_by_id[second_bus_id],
                "parallel_id": extract_branch_parallel_id(str(line_id)),
            }

    return line_data


def build_line_fault_events(
        model: DynawoBlackBoxModel,
        models: Dict[str, DynawoBlackBoxModel],
        connects: List[DynawoConnect],
        parameter_sets: Dict[str, Dict[str, object]],
        network_lines: Dict[str, Dict[str, str]],
) -> Optional[FaultEvents]:
    """
    Build DEEAC fault events for a Dynawo `LineFault` model.
    
    :param model: Dynawo line fault model.
    :param models: Dynawo model definitions.
    :param connects: Dynawo model connections.
    :param parameter_sets: Dynawo parameter sets.
    :param network_lines: Mapping from IIDM line id to bus-name pairs.
    :return: Fault event bundle if the model can be mapped, otherwise ``None``.
    """
    if model.par_id is None or model.static_id is None:
        return None
    else:
        line_parameters: Optional[Dict[str, object]] = parameter_sets.get(model.par_id)
        line_mapping: Optional[Dict[str, str]] = network_lines.get(model.static_id)
        if line_parameters is None or line_mapping is None:
            return None
        else:
            start_time: Optional[float] = get_float_parameter(line_parameters, "line_tBegin")
            end_time: Optional[float] = get_float_parameter(line_parameters, "line_tEnd")
            if end_time is None:
                end_time = get_connected_event_time(model.model_id, models, connects, parameter_sets)
            else:
                end_time = end_time

            if start_time is None:
                return None
            else:
                position: Optional[float] = get_float_parameter(line_parameters, "line_D")
                if position is None:
                    position = 0.5
                else:
                    position = normalize_fault_position(position)
                resistance: float = get_float_parameter(line_parameters, "line_RFaultPu", 0.0)
                reactance: float = get_float_parameter(line_parameters, "line_XFaultPu", 0.0)

                failure_events = list()
                mitigation_events = list()
                parallel_id: str = line_mapping["parallel_id"]
                failure_events.append(
                    LineShortCircuitEvent(
                        time=start_time,
                        first_bus_name=line_mapping["first_bus_name"],
                        second_bus_name=line_mapping["second_bus_name"],
                        parallel_id=parallel_id,
                        fault_position=position,
                        fault_resistance=resistance,
                        fault_reactance=reactance,
                    )
                )
                if end_time is not None:
                    if has_line_switch_off_signal(model.model_id, connects):
                        mitigation_events.append(
                            BranchEvent(
                                time=end_time,
                                first_bus_name=line_mapping["first_bus_name"],
                                second_bus_name=line_mapping["second_bus_name"],
                                parallel_id=parallel_id,
                                breaker_position=BreakerPosition.FIRST_BUS,
                                breaker_closed=False,
                            )
                        )
                        mitigation_events.append(
                            BranchEvent(
                                time=end_time,
                                first_bus_name=line_mapping["second_bus_name"],
                                second_bus_name=line_mapping["first_bus_name"],
                                parallel_id=parallel_id,
                                breaker_position=BreakerPosition.FIRST_BUS,
                                breaker_closed=False,
                            )
                        )
                    else:
                        mitigation_events.append(
                            LineShortCircuitClearingEvent(
                                time=end_time,
                                first_bus_name=line_mapping["first_bus_name"],
                                second_bus_name=line_mapping["second_bus_name"],
                                parallel_id=parallel_id,
                            )
                        )
                else:
                    mitigation_events = mitigation_events

                return FaultEvents(
                    failure_events=failure_events,
                    mitigation_events=mitigation_events,
                    name=model.model_id,
                )


def has_line_switch_off_signal(target_model_id: str, connects: List[DynawoConnect]) -> bool:
    """
    Check whether a Dynawo line fault model receives a switch-off signal.

    In the Dynawo IEEE14 case, the fault is cleared by disconnecting the line.
    When that signal exists, DEEAC must model post-fault topology changes
    instead of only removing the fictive fault loads.

    :param target_model_id: Target fault model id.
    :param connects: Dynawo model connections.
    :return: ``True`` when a switch-off signal is connected.
    """
    for connect in connects:
        if connect.target_id == target_model_id and "line_switchoffsignal" in connect.target_variable.lower():
            return True
        else:
            pass
    return False


def get_connected_event_time(
        target_model_id: str,
        models: Dict[str, DynawoBlackBoxModel],
        connects: List[DynawoConnect],
        parameter_sets: Dict[str, Dict[str, object]],
) -> Optional[float]:
    """
    Get an event end time from an upstream connected event model.
    
    :param target_model_id: Target fault model id.
    :param models: Dynawo model definitions.
    :param connects: Dynawo connection list.
    :param parameter_sets: Dynawo parameter sets keyed by par id.
    :return: Connected event time when available.
    """
    for connect in connects:
        if connect.target_id == target_model_id and "switchoffsignal" in connect.target_variable.lower():
            source_model: Optional[DynawoBlackBoxModel] = models.get(connect.source_id)
            if source_model is not None and source_model.par_id is not None:
                source_parameters: Optional[Dict[str, object]] = parameter_sets.get(source_model.par_id)
                if source_parameters is not None:
                    event_time: Optional[float] = get_float_parameter(source_parameters, "event_tEvent")
                    if event_time is not None:
                        return event_time
                    else:
                        pass
                else:
                    pass
            else:
                pass
        else:
            pass
    return None


def get_float_parameter(
        parameters: Dict[str, object],
        parameter_name: str,
        default_value: Optional[float] = None,
) -> Optional[float]:
    """
    Get a floating-point parameter from a Dynawo parameter set.
    
    :param parameters: Dynawo parameter set.
    :param parameter_name: Parameter name.
    :param default_value: Default value returned when the parameter is absent.
    :return: Floating-point parameter value.
    """
    raw_value: Optional[object] = parameters.get(parameter_name)
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    else:
        return default_value


def normalize_fault_position(position: float) -> float:
    """
    Normalize a Dynawo fault position to the ``0..1`` interval.
    
    :param position: Raw Dynawo fault position.
    :return: Normalized position.
    """
    if position > 1.0:
        return position / 100.0
    else:
        return position


def sanitize_numeric_value(value: object, default_value: float = 0.0) -> float:
    """
    Convert a parsed numeric value to a finite float.

    PowSybl dataframes may contain ``NaN`` for solved quantities that are not
    relevant for a given element. DEEAC network objects expect finite numeric
    values, so missing values must be replaced explicitly.

    :param value: Raw parsed value.
    :param default_value: Value returned when the input is missing or invalid.
    :return: Finite floating-point value.
    """
    if isinstance(value, (int, float)):
        numeric_value: float = float(value)
        if math.isnan(numeric_value):
            return default_value
        else:
            return numeric_value
    else:
        return default_value


def select_slack_generator_id(
        generators,
        bus_dict: Dict[str, Bus],
        eligible_generator_ids: Optional[Set[str]] = None,
) -> Optional[str]:
    """
    Select the IIDM generator that should become the DEEAC slack generator.

    Dynawo IIDM input does not explicitly provide the DEEAC slack generator
    type. The load-flow reference is however visible in the solved bus angles.
    The generator connected to the bus with the reference angle is therefore
    the best explicit slack candidate for the DEEAC model.

    :param generators: PowSybl generators dataframe.
    :param bus_dict: Mapping from IIDM bus identifier to DEEAC bus.
    :param eligible_generator_ids: Optional subset of generator ids eligible to become
                                   the DEEAC slack machine.
    :return: Identifier of the selected slack generator, if any.
    """
    selected_generator_id: Optional[str] = None
    smallest_absolute_angle: Optional[float] = None

    for generator_id, row in generators.iterrows():
        generator_id_str = str(generator_id)
        if eligible_generator_ids is not None and generator_id_str not in eligible_generator_ids:
            continue
        if not row["connected"]:
            continue

        bus_id: str = row["bus_id"]
        bus: Optional[Bus] = bus_dict.get(bus_id)
        if bus is None:
            continue

        absolute_angle: float = abs(bus.phase_angle)
        if selected_generator_id is None:
            selected_generator_id = generator_id_str
            smallest_absolute_angle = absolute_angle
        elif smallest_absolute_angle is not None and absolute_angle < smallest_absolute_angle:
            selected_generator_id = generator_id_str
            smallest_absolute_angle = absolute_angle
        else:
            pass

    return selected_generator_id


class IidmParser:
    """
    DynawoParser.

    Rationale:
        This class handles input parsing or configuration shaping. It converts
        external data into the explicit objects consumed by the EEAC pipeline.

    :ivar fname: IIDM file path.
    :ivar dynawo_parser: Dynawo parser used to augment generator parameters.
    :ivar dynawo_dyd_file: Dynawo .dyd file path.
    """

    def __init__(
            self,
            fname: str,
            dynawo_dyd_file: Optional[str] = None,
            dynawo_par_file: Optional[str] = None,
            dotted_generator_inertia_multiplier: float = 1.0,
    ) -> None:
        """

        :param fname: IIDM file path.
        :param dynawo_dyd_file: Dynawo .dyd file path.
        :param dynawo_par_file: Dynawo .par file path.
        :param dotted_generator_inertia_multiplier: Multiplier applied to
            generators whose IIDM id starts with ``.``.
        """

        if os.path.exists(fname):
            self.ps_grid = pp.network.load(fname)
        else:
            self.ps_grid = None

        self._dynawo_dyd_file = dynawo_dyd_file
        self._dotted_generator_inertia_multiplier = dotted_generator_inertia_multiplier
        if dynawo_dyd_file is not None and dynawo_par_file is not None:
            self._dynawo_parser = DynawoParametersParser(dynawo_dyd_file, dynawo_par_file)
        else:
            self._dynawo_parser = None

    def parse(self) -> Network:
        """
        Convert the PowSybl structures to  deeac
        :return: Network
        """

        grid = Network(base_power=100.0)

        if self.ps_grid is None:
            grid.set_fault_events(self._parse_fault_events_from_dyd())
            return grid
        else:
            # substations = self.ps_grid.get_substations(all_attributes=True)
            voltage_levels = self.ps_grid.get_voltage_levels(all_attributes=True)
            buses = self.ps_grid.get_buses(all_attributes=True)

            lines = self.ps_grid.get_lines(all_attributes=True)
            branches = self.ps_grid.get_branches(all_attributes=True)
            # switches = self.ps_grid.get_switches(all_attributes=True)
            transformers = self.ps_grid.get_2_windings_transformers(all_attributes=True)

            hvdc = self.ps_grid.get_hvdc_lines(all_attributes=True)

            loads = self.ps_grid.get_loads(all_attributes=True)
            gens = self.ps_grid.get_generators(all_attributes=True)
            capacitor_banks = self.ps_grid.get_shunt_compensators(all_attributes=True)
            svc = self.ps_grid.get_static_var_compensators(all_attributes=True)

            """
            Voltage Level
            0 = {str} 'name'
            1 = {str} 'substation_id'
            2 = {str} 'nominal_v'
            3 = {str} 'high_voltage_limit'
            4 = {str} 'low_voltage_limit'
            """
            vl_dict = {i: row["nominal_v"] for i, row in voltage_levels.iterrows()}

            bus_dict = dict()
            for idx, row in buses.iterrows():
                """
                0 = {str} 'name'
                1 = {str} 'v_mag'
                2 = {str} 'v_angle'
                3 = {str} 'connected_component'
                4 = {str} 'synchronous_component'
                5 = {str} 'voltage_level_id'
                6 = {str} 'fictitious'
                """

                vl_id = row["voltage_level_id"]
                name = row["name"] if row["name"] != "" else idx
                if isinstance(name, str):
                    name = normalize_iidm_bus_name(name)
                else:
                    name = str(idx)
                bus = Bus(
                    name=name,
                    base_voltage=vl_dict[vl_id],
                    voltage_magnitude=row["v_mag"],
                    phase_angle=math.radians(float(row["v_angle"])),
                    tpe=None
                )
                grid.add_bus(bus)
                bus_dict[idx] = bus

            for i, row in lines.iterrows():
                """
                00 = {str} 'name'
                01 = {str} 'r'
                02 = {str} 'x'
                03 = {str} 'g1'
                04 = {str} 'b1'
                05 = {str} 'g2'
                06 = {str} 'b2'
                07 = {str} 'p1'
                08 = {str} 'q1'
                09 = {str} 'i1'
                10 = {str} 'p2'
                11 = {str} 'q2'
                12 = {str} 'i2'
                13 = {str} 'voltage_level1_id'
                14 = {str} 'voltage_level2_id'
                15 = {str} 'bus1_id'
                16 = {str} 'bus_breaker_bus1_id'
                17 = {str} 'node1'
                18 = {str} 'bus2_id'
                19 = {str} 'bus_breaker_bus2_id'
                20 = {str} 'node2'
                21 = {str} 'connected1'
                22 = {str} 'connected2'
                23 = {str} 'fictitious'
                24 = {str} 'selected_limits_group_1'
                25 = {str} 'selected_limits_group_2'
                """
                if row["connected1"] and row["connected2"]:
                    bus1 = bus_dict[row["bus1_id"]]
                    bus2 = bus_dict[row["bus2_id"]]
                    line_base_impedance: float = bus1.base_voltage * bus2.base_voltage / grid.base_power

                    grid.add_branch(sending_bus=bus1,
                                    receiving_bus=bus2,
                                    element=Line(
                                        base_impedance=line_base_impedance,
                                        resistance=row["r"],
                                        reactance=row["x"],
                                        shunt_conductance=row["g1"] + row["g2"],
                                        shunt_susceptance=row["b1"] + row["b2"],
                                        closed_at_first_bus=True,
                                        closed_at_second_bus=True
                                    ),
                                    parallel_id=extract_branch_parallel_id(str(i)))

            for i, row in transformers.iterrows():
                """
                00 = {str} 'name'
                01 = {str} 'r'
                02 = {str} 'x'
                03 = {str} 'g'
                04 = {str} 'b'
                05 = {str} 'rated_u1'
                06 = {str} 'rated_u2'
                07 = {str} 'rated_s'
                08 = {str} 'p1'
                09 = {str} 'q1'
                10 = {str} 'i1'
                11 = {str} 'p2'
                12 = {str} 'q2'
                13 = {str} 'i2'
                14 = {str} 'voltage_level1_id'
                15 = {str} 'voltage_level2_id'
                16 = {str} 'bus1_id'
                17 = {str} 'bus_breaker_bus1_id'
                18 = {str} 'node1'
                19 = {str} 'bus2_id'
                20 = {str} 'bus_breaker_bus2_id'
                21 = {str} 'node2'
                22 = {str} 'connected1'
                23 = {str} 'connected2'
                24 = {str} 'fictitious'
                25 = {str} 'selected_limits_group_1'
                26 = {str} 'selected_limits_group_2'
                27 = {str} 'rho'
                28 = {str} 'alpha'
                29 = {str} 'r_at_current_tap'
                30 = {str} 'x_at_current_tap'
                31 = {str} 'g_at_current_tap'
                32 = {str} 'b_at_current_tap'
                """
                if row["connected1"] and row["connected2"]:
                    bus1 = bus_dict[row["bus1_id"]]
                    bus2 = bus_dict[row["bus2_id"]]
                    transformer_base_impedance: float = bus2.base_voltage ** 2 / grid.base_power
                    transformer_ratio: float
                    if bus1.voltage_magnitude != 0 and bus2.voltage_magnitude != 0:
                        transformer_ratio = (
                                (bus1.base_voltage / bus1.voltage_magnitude) *
                                (bus2.voltage_magnitude / bus2.base_voltage)
                        )
                    else:
                        transformer_ratio = 1.0
                    grid.add_branch(sending_bus=bus1,
                                    receiving_bus=bus2,
                                    element=Transformer(
                                        sending_node=bus1.name,
                                        receiving_node=bus2.name,
                                        base_impedance=transformer_base_impedance,
                                        resistance=row["r_at_current_tap"],
                                        reactance=row["x_at_current_tap"],
                                        shunt_conductance=row["g_at_current_tap"],
                                        shunt_susceptance=row["b_at_current_tap"],
                                        phase_shift_angle=row["alpha"],
                                        ratio=transformer_ratio,
                                        initial_tap_number=0,
                                        closed_at_first_bus=True,
                                        closed_at_second_bus=True,
                                        transformer_type=1,
                                    ),
                                    parallel_id=extract_branch_parallel_id(str(i)))

            for i, row in hvdc.iterrows():
                """
                00 = {str} 'name'
                01 = {str} 'converters_mode'
                02 = {str} 'target_p'
                03 = {str} 'max_p'
                04 = {str} 'nominal_v'
                05 = {str} 'r'
                06 = {str} 'converter_station1_id'
                07 = {str} 'converter_station2_id'
                08 = {str} 'connected1'
                09 = {str} 'connected2'
                10 = {str} 'fictitious'
                """
                bus1 = bus_dict[[v for v in bus_dict if row["converter_station2_id"][0:7] in v][0]]
                grid.add_hvdc_converter(
                    Load(
                        name=i,
                        bus=bus1,
                        connected=row["connected2"],
                        active_power=row["target_p"],
                        reactive_power=0,
                    )
                )

            for i, row in loads.iterrows():
                """
                00 = {str} 'name'
                01 = {str} 'type'
                02 = {str} 'p0'
                03 = {str} 'q0'
                04 = {str} 'p'
                05 = {str} 'q'
                06 = {str} 'i'
                07 = {str} 'voltage_level_id'
                08 = {str} 'bus_id'
                09 = {str} 'bus_breaker_bus_id'
                10 = {str} 'node'
                11 = {str} 'connected'
                12 = {str} 'fictitious'
                """
                if "fict_" in row.name:
                    a=1
                if row["connected"] and not math.isnan(row.p):
                    bus1 = bus_dict[row["bus_id"]]
                    grid.add_load(
                        Load(
                            name=row.name,
                            bus=bus1,
                            connected=row["connected"],
                            active_power=sanitize_numeric_value(row["p"]),
                            reactive_power=sanitize_numeric_value(row["q"]),
                        )
                    )

            # parse dynawo stuff
            if self._dynawo_parser is None:
                dynawo_data = None
            else:
                dynawo_data = self._dynawo_parser.parse()

            dynamic_generator_ids: Optional[Set[str]]
            if dynawo_data is None:
                dynamic_generator_ids = None
            else:
                dynamic_generator_ids = {
                    str(generator_id)
                    for generator_id, row in gens.iterrows()
                    if dynawo_data.has_dynamic_generator(str(generator_id))
                    or dynawo_data.has_dynamic_generator(str(row["name"]))
                }

            slack_generator_id: Optional[str] = select_slack_generator_id(
                gens,
                bus_dict,
                eligible_generator_ids=dynamic_generator_ids,
            )

            for i, row in gens.iterrows():
                """
                00 = {str} 'name'
                01 = {str} 'energy_source'
                02 = {str} 'target_p'
                03 = {str} 'min_p'
                04 = {str} 'max_p'
                05 = {str} 'min_q'
                06 = {str} 'max_q'
                07 = {str} 'min_q_at_target_p'
                08 = {str} 'max_q_at_target_p'
                09 = {str} 'min_q_at_p'
                10 = {str} 'max_q_at_p'
                11 = {str} 'rated_s'
                12 = {str} 'reactive_limits_kind'
                13 = {str} 'target_v'
                14 = {str} 'target_q'
                15 = {str} 'voltage_regulator_on'
                16 = {str} 'regulated_element_id'
                17 = {str} 'regulated_bus_id'
                18 = {str} 'regulated_bus_breaker_bus_id'
                19 = {str} 'p'
                20 = {str} 'q'
                21 = {str} 'i'
                22 = {str} 'voltage_level_id'
                23 = {str} 'bus_id'
                24 = {str} 'bus_breaker_bus_id'
                25 = {str} 'node'
                26 = {str} 'condenser'
                27 = {str} 'connected'
                28 = {str} 'fictitious'
                """
                if row["connected"]:
                    bus1 = bus_dict[row["bus_id"]]
                    generator_id = str(i)
                    generator_name = row["name"] if row["name"] != "" else generator_id
                    generator_source: GeneratorSource = parse_generator_source(str(row["energy_source"]))

                    if dynawo_data is not None:
                        dynawo_params = dynawo_data.get_generator_parameters(generator_id)
                        if dynawo_params is None:
                            dynawo_params = dynawo_data.get_generator_parameters(generator_name)

                        is_dynamic_generator = (
                            dynawo_data.has_dynamic_generator(generator_id)
                            or dynawo_data.has_dynamic_generator(generator_name)
                        )
                        if not is_dynamic_generator:
                            grid.add_load(
                                Load(
                                    name=f"GEN_{generator_name}",
                                    bus=bus1,
                                    connected=row["connected"],
                                    active_power=-sanitize_numeric_value(row["target_p"]),
                                    reactive_power=-sanitize_numeric_value(row["target_q"]),
                                )
                            )
                            continue

                        machine_side_voltage: float
                        if dynawo_params.machine_side_voltage is not None:
                            machine_side_voltage = dynawo_params.machine_side_voltage
                        else:
                            machine_side_voltage = bus1.base_voltage
                        apparent_power_base: float
                        if dynawo_params.rated_apparent_power is not None:
                            apparent_power_base = dynawo_params.rated_apparent_power
                        else:
                            apparent_power_base = grid.base_power
                        base_impedance = machine_side_voltage ** 2 / apparent_power_base
                        direct_transient_reactance = (
                                dynawo_params.direct_transient_reactance_pu * base_impedance
                        )
                        if dynawo_params.rated_apparent_power is not None:
                            inertia_constant = (
                                    dynawo_params.inertia_constant *
                                    dynawo_params.rated_apparent_power /
                                    grid.base_power
                            )
                        else:
                            inertia_constant = dynawo_params.inertia_constant
                    else:
                        direct_transient_reactance = 0.01
                        inertia_constant = 0.0

                    generator_type: GeneratorType
                    if str(i) == slack_generator_id:
                        generator_type = GeneratorType.SLACK
                    else:
                        if row["voltage_regulator_on"]:
                            generator_type = GeneratorType.PV
                        else:
                            generator_type = GeneratorType.PQ

                    if generator_id.startswith("."):
                        inertia_constant = (
                            inertia_constant * self._dotted_generator_inertia_multiplier
                        )

                    grid.add_generator(
                        Generator(
                            name=generator_name,
                            bus=bus1,
                            connected=row["connected"],
                            active_power=sanitize_numeric_value(row["target_p"]),
                            max_active_power=sanitize_numeric_value(row["max_p"]),
                            reactive_power=sanitize_numeric_value(row["target_q"]),
                            direct_transient_reactance=direct_transient_reactance,
                            inertia_constant=inertia_constant,
                            regulating=row["voltage_regulator_on"],
                            tpe=generator_type,
                            source=generator_source,
                        )
                    )

            for i, row in capacitor_banks.iterrows():
                """
                00 = {str} 'name'
                01 = {str} 'g'
                02 = {str} 'b'
                03 = {str} 'model_type'
                04 = {str} 'max_section_count'
                05 = {str} 'section_count'
                06 = {str} 'solved_section_count'
                07 = {str} 'voltage_regulation_on'
                08 = {str} 'target_v'
                09 = {str} 'target_deadband'
                10 = {str} 'regulating_bus_id'
                11 = {str} 'p'
                12 = {str} 'q'
                13 = {str} 'i'
                14 = {str} 'voltage_level_id'
                15 = {str} 'bus_id'
                16 = {str} 'bus_breaker_bus_id'
                17 = {str} 'node'
                18 = {str} 'connected'
                19 = {str} 'fictitious'
                """
                if row["connected"] and not math.isnan(row.q):
                    bus1 = bus_dict[row["bus_id"]]
                    grid.add_capacitor_bank(
                        CapacitorBank(
                            name=row.name,
                            bus=bus1,
                            active_power=sanitize_numeric_value(row["p"]),
                            reactive_power=sanitize_numeric_value(row["q"])
                        )
                    )

            for i, row in svc.iterrows():
                """
                00 = {str} 'name'
                01 = {str} 'b_min'
                02 = {str} 'b_max'
                03 = {str} 'target_v'
                04 = {str} 'target_q'
                05 = {str} 'regulation_mode'
                06 = {str} 'regulating'
                07 = {str} 'regulated_element_id'
                08 = {str} 'regulated_bus_id'
                09 = {str} 'regulated_bus_breaker_bus_id'
                10 = {str} 'p'
                11 = {str} 'q'
                12 = {str} 'i'
                13 = {str} 'voltage_level_id'
                14 = {str} 'bus_id'
                15 = {str} 'bus_breaker_bus_id'
                16 = {str} 'node'
                17 = {str} 'connected'
                18 = {str} 'fictitious'
                """
                if row["connected"]:
                    bus1 = bus_dict[row["bus_id"]]
                    grid.add_static_var_compensator(
                        CapacitorBank(
                            name=row.name,
                            bus=bus1,
                            active_power=sanitize_numeric_value(row["p"]),
                            reactive_power=sanitize_numeric_value(row["q"])
                        )
                    )

            # load_flow = Loa

            # Create the network based on a network topology and load flow data
            grid.set_fault_events(self._parse_fault_events_from_dyd())
            return grid

    def _parse_fault_events_from_dyd(self) -> List[FaultEvents]:
        """
        Parse fault events from the Dynawo .dyd file.

        :return: List of fault event bundles.
        """
        if self._dynawo_dyd_file is None or not os.path.exists(self._dynawo_dyd_file):
            return []
        try:
            root = ET.parse(self._dynawo_dyd_file).getroot()
        except ET.ParseError:
            return []

        events_by_group: Dict[str, List[object]] = defaultdict(list)
        for element in root.iter():
            tag_name = self._strip_namespace(element.tag).lower()
            if not self._is_fault_tag(tag_name):
                continue
            event = self._build_fault_event_from_element(element)
            if event is None:
                continue
            group_id = self._get_attr(element, ["faultId", "fault_id", "scenario", "group", "id"])
            if not group_id:
                group_id = "fault_1"
            events_by_group[group_id].append(event)

        fault_events: List[FaultEvents] = []
        for group_id, events in events_by_group.items():
            failure_events = []
            mitigation_events = []
            for event in events:
                if isinstance(event, MitigationEvent):
                    mitigation_events.append(event)
                else:
                    failure_events.append(event)
            if not failure_events and not mitigation_events:
                continue
            fault_events.append(
                FaultEvents(
                    failure_events=failure_events,
                    mitigation_events=mitigation_events,
                    name=group_id,
                )
            )
        return fault_events

    def _build_fault_event_from_element(self, element: ET.Element) -> Optional[object]:
        """
        Build a fault event from a Dynawo XML element.

        :param element: XML element.
        :return: Parsed event or None.
        """
        event_type = self._get_attr(element, ["type", "eventType", "event_type", "kind", "faultType"])
        if event_type is None:
            event_type = self._get_attr(element, ["lib"])
        time = self._get_float_attr(element, ["time", "t", "eventTime", "event_time", "startTime"])
        if event_type is None or time is None:
            return None

        event_type = event_type.strip().lower().replace("-", "_")
        if event_type in {"bus_fault", "node_fault", "bus_short_circuit"} or "busfault" in event_type:
            bus_name = self._get_attr(element, ["bus", "bus_name", "busName", "node", "node_name", "nodeName"])
            if not bus_name:
                return None
            resistance = self._get_float_attr(element, ["resistance", "r", "fault_resistance", "faultResistance"], 0.0)
            reactance = self._get_float_attr(element, ["reactance", "x", "fault_reactance", "faultReactance"], 0.0)
            return BusShortCircuitEvent(
                time=time,
                bus_name=bus_name,
                fault_resistance=resistance,
                fault_reactance=reactance,
            )

        if event_type in {"bus_clear", "node_clear", "bus_short_circuit_clearing"} or "busclear" in event_type:
            bus_name = self._get_attr(element, ["bus", "bus_name", "busName", "node", "node_name", "nodeName"])
            if not bus_name:
                return None
            return BusShortCircuitClearingEvent(time=time, bus_name=bus_name)

        if event_type in {"line_fault", "line_short_circuit"} or "linefault" in event_type:
            first_bus = self._get_attr(
                element,
                ["sending_node", "sendingNode", "from", "bus1", "first_bus", "firstBus"],
            )
            second_bus = self._get_attr(
                element,
                ["receiving_node", "receivingNode", "to", "bus2", "second_bus", "secondBus"],
            )
            if not first_bus or not second_bus:
                return None
            parallel_id = self._get_attr(
                element,
                ["parallel_id", "parallelId", "parallel_index", "parallelIndex"],
            ) or "0"
            position = self._get_float_attr(
                element,
                ["fault_position", "faultPosition", "distance", "short_circuit_distance", "shortCircuitDistance"],
            )
            if position is None:
                position = 0.5
            if position > 1.0:
                position /= 100.0
            if position <= 0.0 or position >= 1.0:
                return None
            resistance = self._get_float_attr(element, ["resistance", "r", "fault_resistance", "faultResistance"], 0.0)
            reactance = self._get_float_attr(element, ["reactance", "x", "fault_reactance", "faultReactance"], 0.0)
            return LineShortCircuitEvent(
                time=time,
                first_bus_name=first_bus,
                second_bus_name=second_bus,
                parallel_id=parallel_id,
                fault_position=position,
                fault_resistance=resistance,
                fault_reactance=reactance,
            )

        if event_type in {"line_clear", "line_short_circuit_clearing"} or "lineclear" in event_type:
            first_bus = self._get_attr(
                element,
                ["sending_node", "sendingNode", "from", "bus1", "first_bus", "firstBus"],
            )
            second_bus = self._get_attr(
                element,
                ["receiving_node", "receivingNode", "to", "bus2", "second_bus", "secondBus"],
            )
            if not first_bus or not second_bus:
                return None
            parallel_id = self._get_attr(
                element,
                ["parallel_id", "parallelId", "parallel_index", "parallelIndex"],
            ) or "0"
            return LineShortCircuitClearingEvent(
                time=time,
                first_bus_name=first_bus,
                second_bus_name=second_bus,
                parallel_id=parallel_id,
            )

        if event_type in {"breaker_open", "breaker_opening"} or "breakeropen" in event_type:
            first_bus = self._get_attr(
                element,
                ["first_bus", "firstBus", "bus1", "from", "sending_node", "sendingNode"],
            )
            second_bus = self._get_attr(
                element,
                ["second_bus", "secondBus", "bus2", "to", "receiving_node", "receivingNode"],
            )
            if not first_bus or not second_bus:
                return None
            parallel_id = self._get_attr(
                element,
                ["parallel_id", "parallelId", "parallel_index", "parallelIndex"],
            ) or "0"
            return BreakerEvent(
                time=time,
                first_bus_name=first_bus,
                second_bus_name=second_bus,
                parallel_id=parallel_id,
                breaker_closed=False,
            )

        if event_type in {"breaker_close", "breaker_closing"} or "breakerclose" in event_type:
            first_bus = self._get_attr(
                element,
                ["first_bus", "firstBus", "bus1", "from", "sending_node", "sendingNode"],
            )
            second_bus = self._get_attr(
                element,
                ["second_bus", "secondBus", "bus2", "to", "receiving_node", "receivingNode"],
            )
            if not first_bus or not second_bus:
                return None
            parallel_id = self._get_attr(
                element,
                ["parallel_id", "parallelId", "parallel_index", "parallelIndex"],
            ) or "0"
            return BreakerEvent(
                time=time,
                first_bus_name=first_bus,
                second_bus_name=second_bus,
                parallel_id=parallel_id,
                breaker_closed=True,
            )

        return None

    def _get_attr(self, element: ET.Element, names: Sequence[str]) -> Optional[str]:
        """
        Return the first matching attribute value.

        :param element: XML element.
        :param names: Attribute names to test.
        :return: Attribute value if found.
        """
        for name in names:
            value = element.get(name)
            if value:
                return value
        return None

    def _get_float_attr(self, element: ET.Element, names: Sequence[str], default: Optional[float] = None) -> Optional[
        float]:
        """
        Return the first matching attribute parsed as float.

        :param element: XML element.
        :param names: Attribute names to test.
        :param default: Default value if not found or not parseable.
        :return: Parsed float value if found.
        """
        raw_value = self._get_attr(element, names)
        if raw_value is None:
            return default
        try:
            return float(raw_value)
        except ValueError:
            return default

    def _strip_namespace(self, tag: str) -> str:
        """
        Strip XML namespace from a tag.

        :param tag: Tag name.
        :return: Namespace-free tag.
        """
        return tag.split("}")[-1]

    def _is_fault_tag(self, tag_name: str) -> bool:
        """
        Check whether a tag name looks like a fault/event definition.

        :param tag_name: Tag name.
        :return: True if tag name suggests a fault/event definition.
        """
        return tag_name in {"event", "fault", "blackboxmodel"} or tag_name.endswith("event") or tag_name.endswith(
            "fault")
