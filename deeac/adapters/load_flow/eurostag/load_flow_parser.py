# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import re
from enum import Enum
from typing import Dict
from pydantic import ValidationError

from deeac.adapters.load_flow.eurostag import dtos as eurostag_dtos
from deeac.adapters.load_flow.eurostag.exceptions import LoadFlowTransformerException
from deeac.domain.ports.load_flow import LoadFlowParser
from deeac.domain.ports.dtos import Value, Unit
from deeac.domain.ports.dtos.load_flow import (
    LoadFlowResults, Bus, Generator, Transformer, TransformerNodeData,
    TransformerTapData, StaticVarCompensator, HVDCConverter, Load
)
from deeac.domain.ports.exceptions import (
    NetworkElementNameException, BranchParallelException
)
from deeac.domain.exceptions import DEEACExceptionCollector, DEEACExceptionList
from .table_description import LOAD_FLOW_TABLE_DELIMITER, TableDescription, TableType
from .exceptions import LoadFlowDataValidationException, LoadFlowDivergenceException

# Pattern used to identify voltage and angle columns that do not respect the format
VOLTAGE_SL_RESULT_PATTERN = re.compile("^(\\|\\s+\\|\\s+)SL(\\s+\\|.*)$")

# Pattern used to identify disconnected elements
DISCONNECTED_RESULT_PATTERN = re.compile("^.*\\|\\s*OUT\\s*\\|.*$")
FILE_DESCRIPTION = {
    TableType.TRANSFORMERS: TableDescription(
        names=["TRANSFORMATEUR(S)", "TRANSFORMER(S)"],
        first_data_row_nb=4,
        row_format={
            'sending_node': (1, -1, None),
            'receiving_node': (2, -1, None),
            'parallel_index': (3, -1, None),
            'type': (5, -1, None)
        },
        load_flow_data=eurostag_dtos.Transformer,
        data_occurences=(2, 5)
    ),
    TableType.TRANSFORMERSNODEDATA: TableDescription(
        names=["LISTING ENTREES", "GENERAL INPUT LISTING"],
        first_data_row_nb=5,
        row_format={
            'orig_node': (1, 8, 5),
            'orig_zone': (1, 2, 0),
            'node': (5, 8, 3),
            'zone': (5, 2, 0),
            'parallel_index': (5, 1, 14),
            'type': (6, -1, None),
            'resistance': (7, 6, 0),
            'reactance': (7, 7, 7),
            'shunt_conductance': (8, 4, 0),
            'shunt_susceptance': (8, 7, 5)
        },
        load_flow_data=eurostag_dtos.TransformerNodeData
    ),
    TableType.TRANSFORMERTAPDATA: TableDescription(
        names=["TRANSFORMATEUR(S) A CHANGEUR DE PRISES EN CHARGE"],
        first_data_row_nb=5,
        row_format={
            'sending_node': (1, -1, None),
            'receiving_node': (2, -1, None),
            'parallel_index': (3, -1, None),
            'tap_number': (9, -1, None),
            'phase_angle': (13, -1, None),
            'sending_node_voltage': (10, -1, None),
            'receiving_node_voltage': (11, -1, None)
        },
        load_flow_data=eurostag_dtos.TransformerTapData
    ),
    TableType.HVDC_CONVERTERS_RESULTS: TableDescription(
        names=["RESULTATS DES CONVERTISSEURS"],
        strict_match_names=False,
        first_data_row_nb=9,
        row_format={
            'converter_name': (1, -1, None),
            'active_power': (7, -1, None),
            'reactive_power': (8, -1, None)
        },
        load_flow_data=eurostag_dtos.HVDCConverter
    ),
    TableType.RESULTS: TableDescription(
        names=["RESULTATS COMPLETS", "GENERAL OUTPUT LISTING"],
        first_data_row_nb=6,
        row_format={
            'area': (1, 2, 0),
            'node_name': (1, 8, 3),
            'voltage': (2, 6, 0),
            'phase_angle': (2, 7, 6),
            'production_active_power': (3, 8, 0),
            'production_reactive_power': (3, 8, 9),
            'load_active_power': (4, -1, 0),
            'load_reactive_power': (4, -1, 1),
            'connected_node_name': (5, 8, 3),
            'branch_parallel_index': (5, 1, 12),
            'transformer_tap': (9, -1, None)
        },
        load_flow_data=eurostag_dtos.Result
    )
}

# Description of the table of interest in the file


class ElementType(Enum):
    """
    Element type is encoded in the 'area' field of a load flow result, if the element is not a bus.
    In case of a bus, no type is specified, but an area is given. This is the reason why bus is not part of this enum.
    """
    BANK = "CA"
    VSC_CONVERTER = "VS"
    CSC_CONVERTER = "CS"
    GENERATOR = "GE"
    SVC = "SV"
    LOAD = "LO"


class EurostagLoadFlowParser(LoadFlowParser):
    """
    Parse the results of a load flow analysis performed by Eurostag.
    These results are obtained from a .lf file.
    """

    def __init__(self, load_flow_results_file: str, load_flow_input_file: str = None):
        """
        Initialize the parser.

        :param load_flow_results_file: Output file where load flow results computed with Eurostag must be stored.
        :param load_flow_input_file: Input file with static data used to run a load flow.
        """
        self.load_flow_input_file = load_flow_input_file
        self.load_flow_results_file = load_flow_results_file

        # Load flow parsing data
        self._current_table_description = None
        self._table_row_nb = 0
        self._check_table_name = True

        # Output data part of the load flow results
        self._generators = {}
        self._transformers = {}
        self._transformer_nodes_data = {}
        self._transformer_tap_data = {}
        self._buses = {}
        self._loads = {}

        # Transformers nodes and taps to identify
        self._transformer_info = []
        self._transformer_taps = []
        self._transformer_nodes = []

        # Current origin node for a branch in results analysis
        self._current_origin_node_name = None

        # Exception collector
        self._exception_collector: DEEACExceptionCollector = DEEACExceptionCollector()

        # Generate element types only once to increase performances
        self._elements_types = {}
        for type in ElementType:
            self._elements_types[type.value] = type

        self._divergence_error = "ERR-019.0461"
        self._page_number_removal = str.maketrans('0123456789', '          ')

    def _reset_parser(self):
        """
        Reset parser so that it can read a new file.
        """
        self._transformer_info.clear()
        self._current_origin_node_name = None
        self._exception_collector.reset()
        self._generators = {}
        self._loads = {}
        self._transformers = {}
        self._transformer_nodes_data = {}
        self._transformer_tap_data = {}
        self._transformer_taps = []
        self._transformer_info = []
        self._buses = {}
        self._hvdc_converters = {}
        self._static_var_compensators = {}

    def _run_load_flow(self):
        """
        Run a load flow based on the data found in an input file.
        """
        pass

    def _raise_if_duplicated(self, name: str, container: Dict, object_type: str):
        """
        Raise a NetworkElementNameException if an object was already observed with the same name.

        :param name: Name of the object.
        :param container: Dictionary containing the objects mapped to their named.
        :param object_type: Type of the object to check.
        :raise NetworkElementNameException if an object in the container has already the same name.
        """
        if name in container:
            raise NetworkElementNameException(name, object_type)

    def _raise_validation_errors(self, e: ValidationError, load_flow_data: eurostag_dtos.LoadFlowData):
        """
        Raise an ExceptionList with validation errors raised when trying to map load flow data to a Pydantic model.

        :param e: Validation error to raise.
        :param load_flow_data: LoadFlowData at the origin of the error.
        :raise ExceptionList with the errors.
        """
        exception_list = DEEACExceptionList([])
        # Get validation errors and create corresponding DEEAC exceptions
        for val_error in e.errors():
            exception_list.append(
                LoadFlowDataValidationException(load_flow_data.dict(), val_error["loc"], val_error["type"])
            )
        raise(exception_list)

    def _analyse_load_flow_data(self, load_flow_data: eurostag_dtos.LoadFlowData):
        """
        Analyse load flow data to extract data of interest.

        :param load_flow_data: Load flow data to analyse.
        """
        if type(load_flow_data) == eurostag_dtos.Transformer:
            # Extract transformer node names, only for detailed transformers
            if load_flow_data.type == eurostag_dtos.TransformerType.DETAILED:
                self._transformer_info.append((
                    load_flow_data.sending_node,
                    load_flow_data.receiving_node,
                    load_flow_data.parallel_index
                ))
        elif type(load_flow_data) == eurostag_dtos.TransformerNodeData:
            if load_flow_data.orig_node is not None:
                if load_flow_data.orig_zone in ("GE", "LO", "CA", "SV"):
                    return
                self._raise_if_duplicated(load_flow_data.orig_node, self._transformer_nodes_data, TransformerNodeData.__name__)
                self._transformer_nodes.append(f"{load_flow_data.orig_zone}_{load_flow_data.orig_node}")
                self._transformer_nodes_data[load_flow_data.orig_node] = TransformerNodeData(
                    orig_node=load_flow_data.orig_node,
                    zone=load_flow_data.orig_zone,
                    parallel_ids=list(),
                    types=list(),
                    nodes=list(),
                    resistances=list(),
                    reactances=list(),
                    shunt_susceptances=list(),
                    shunt_conductances=list()
                )

            elif load_flow_data.type not in (
                eurostag_dtos.TransformerType.DETAILED, eurostag_dtos.TransformerType.FIXED_REAL_RATIO
            ):
                return

            else:
                orig_zone, orig_node = self._transformer_nodes[-1].split("_", 1)
                if load_flow_data.zone in ("GE", "LO", "CA", "SV"):
                    return

                if orig_zone != load_flow_data.zone:
                    raise ValueError(f"Zone incoherence for {load_flow_data.orig_node} in load flow data")

                self._transformer_nodes_data[orig_node].parallel_ids.append(load_flow_data.parallel_index)
                self._transformer_nodes_data[orig_node].types.append(load_flow_data.type)
                self._transformer_nodes_data[orig_node].nodes.append(load_flow_data.node)
                self._transformer_nodes_data[orig_node].resistances.append(load_flow_data.resistance)
                self._transformer_nodes_data[orig_node].reactances.append(load_flow_data.reactance)
                self._transformer_nodes_data[orig_node].shunt_susceptances.append(load_flow_data.shunt_susceptance)
                self._transformer_nodes_data[orig_node].shunt_conductances.append(load_flow_data.shunt_conductance)

        elif type(load_flow_data) == eurostag_dtos.TransformerTapData:
            if load_flow_data.sending_node is not None:
                tap_name = f"{load_flow_data.receiving_node}_{load_flow_data.sending_node}_{load_flow_data.parallel_index}"
                self._transformer_taps.append(tap_name)
                self._transformer_tap_data[tap_name] = TransformerTapData(
                    sending_node=load_flow_data.sending_node,
                    receiving_node=load_flow_data.receiving_node,
                    tap_numbers=list(),
                    phase_angles=list(),
                    sending_node_voltages=list(),
                    receiving_node_voltages=list()
                )
            else:
                tap_name = self._transformer_taps[-1]
                self._transformer_tap_data[tap_name].tap_numbers.append(load_flow_data.tap_number)
                self._transformer_tap_data[tap_name].phase_angles.append(load_flow_data.phase_angle)
                self._transformer_tap_data[tap_name].sending_node_voltages.append(load_flow_data.sending_node_voltage)
                self._transformer_tap_data[tap_name].receiving_node_voltages.append(load_flow_data.receiving_node_voltage)

        elif type(load_flow_data) == eurostag_dtos.HVDCConverter:
            # High voltage direct current converter
            self._raise_if_duplicated(load_flow_data.converter_name, self._hvdc_converters, HVDCConverter.__name__)
            try:
                self._hvdc_converters[load_flow_data.converter_name] = HVDCConverter(
                    name=load_flow_data.converter_name,
                    active_power=Value(value=load_flow_data.active_power, unit=Unit.MW),
                    reactive_power=Value(value=load_flow_data.reactive_power, unit=Unit.MVAR)
                )
            except ValidationError as e:
                self._raise_validation_errors(e, load_flow_data)
        elif type(load_flow_data) == eurostag_dtos.Result:
            # Get element type
            if load_flow_data.area in self._elements_types:
                element_type = self._elements_types[load_flow_data.area]
            else:
                # Element is unknown
                element_type = None

            if element_type is None and load_flow_data.node_name is not None:
                # Data associated to a bus
                self._raise_if_duplicated(load_flow_data.node_name, self._buses, Bus.__name__)
                if load_flow_data.voltage == 0:
                    # Skip if voltage is 0 (probably disconnected)
                    return
                try:
                    self._buses[load_flow_data.node_name] = Bus(
                        name=load_flow_data.node_name,
                        voltage=Value(value=load_flow_data.voltage, unit=Unit.KV),
                        phase_angle=Value(value=load_flow_data.phase_angle, unit=Unit.DEG)
                    )
                except ValidationError as e:
                    self._raise_validation_errors(e, load_flow_data)
                # Update current origin node name
                self._current_origin_node_name = load_flow_data.node_name
            elif element_type == ElementType.GENERATOR:
                # Data associated to a PV generator
                self._raise_if_duplicated(load_flow_data.node_name, self._generators, Generator.__name__)
                try:
                    self._generators[load_flow_data.node_name] = Generator(
                        name=load_flow_data.node_name,
                        active_power=Value(value=load_flow_data.production_active_power, unit=Unit.MW),
                        reactive_power=Value(value=load_flow_data.production_reactive_power, unit=Unit.MVAR)
                    )
                except ValidationError as e:
                    self._raise_validation_errors(e, load_flow_data)
            elif element_type == ElementType.LOAD:
                # Data associated to a PV load
                self._raise_if_duplicated(load_flow_data.node_name, self._loads, Load.__name__)
                try:
                    self._loads[load_flow_data.node_name] = Load(
                        name=load_flow_data.node_name,
                        active_power=Value(value=load_flow_data.load_active_power, unit=Unit.MW),
                        reactive_power=Value(value=load_flow_data.load_reactive_power, unit=Unit.MVAR)
                    )
                except ValidationError as e:
                    self._raise_validation_errors(e, load_flow_data)
            elif element_type == ElementType.SVC:
                # Data associated to a static var compensator
                self._raise_if_duplicated(
                    load_flow_data.node_name,
                    self._static_var_compensators,
                    StaticVarCompensator.__name__
                )
                try:
                    self._static_var_compensators[load_flow_data.node_name] = StaticVarCompensator(
                        name=load_flow_data.node_name,
                        reactive_power=Value(value=load_flow_data.production_reactive_power, unit=Unit.MVAR)
                    )
                except ValidationError as e:
                    self._raise_validation_errors(e, load_flow_data)
            elif load_flow_data.node_name is None:
                # Data associated to a branch, get origin node
                if self._current_origin_node_name is None:
                    raise LoadFlowTransformerException(load_flow_data.connected_node_name)
                connected_node_name = load_flow_data.connected_node_name
                tfo_id = (self._current_origin_node_name, connected_node_name, load_flow_data.branch_parallel_index)
                if tfo_id not in self._transformer_info:
                    # Branch must not be considered
                    return
                if tfo_id in self._transformers:
                    # This parallel transformer was already observed
                    raise BranchParallelException(
                        self._current_origin_node_name, connected_node_name, load_flow_data.branch_parallel_index
                    )
                try:
                    self._transformers[tfo_id] = Transformer(
                        sending_bus=self._current_origin_node_name,
                        receiving_bus=load_flow_data.connected_node_name,
                        parallel_id=load_flow_data.branch_parallel_index,
                        tap_number=load_flow_data.transformer_tap
                    )
                except ValidationError as e:
                    self._raise_validation_errors(e, load_flow_data)

    def parse_load_flow(self) -> LoadFlowResults:
        """
        Parse the results of the load flow analysis.

        :return: The load flow results.
        """
        self._reset_parser()

        # Reinitialize the load flow parsing data between executions
        self._current_table_description = None
        self._table_row_nb = 0
        self._check_table_name = True

        try:
            with open(self.load_flow_results_file, encoding='utf-8') as file:
                for line in file:
                    self._parse_line(line)

        except UnicodeDecodeError:
            with open(self.load_flow_results_file, encoding='latin-1') as file:
                for line in file:
                    self._parse_line(line)

        # Raise exceptions if any
        self._exception_collector.raise_for_exception()

        # Return results
        return LoadFlowResults(
            buses=self._buses,
            loads=self._loads,
            generators=self._generators,
            transformers=self._transformers,
            static_var_compensators=self._static_var_compensators,
            hvdc_converters=self._hvdc_converters,
            transformer_nodes_data=self._transformer_nodes_data,
            transformer_tap_data=self._transformer_tap_data
        )

    def _parse_line(self, line: str):
        """
        Parses the content of one line of the load flow result file
        :param line: one line of the load flow file to parse
        """
        if self._divergence_error in line:
            raise LoadFlowDivergenceException

        line = line.strip()
        # Pass empty lines
        if not line:
            # Tables are separated with blank lines
            self._check_table_name = True
            return

        if self._current_table_description is None:
            if line.startswith(LOAD_FLOW_TABLE_DELIMITER) or not self._check_table_name:
                # Do not check table name
                return
            # Check if new table of interest
            for table in TableType:
                if FILE_DESCRIPTION[table].pattern.match(line.translate(self._page_number_removal)):
                    self._current_table_description = FILE_DESCRIPTION[table]
                    self._table_row_nb = 0
                    break
                self._check_table_name = False
            return
        else:
            self._table_row_nb += 1
            if self._table_row_nb < self._current_table_description.first_data_row_nb:
                # Skip header of the table
                return
            # Ignore delimitation lines
            if LOAD_FLOW_TABLE_DELIMITER in line:
                if line.startswith(LOAD_FLOW_TABLE_DELIMITER):
                    self._current_table_description = None
                    # End of table
                return


        # Disconnected device are ignored
        if DISCONNECTED_RESULT_PATTERN.match(line):
            return

        # Second column of complete results may not respect the format and just be 'SL'
        if VOLTAGE_SL_RESULT_PATTERN.match(line):
            line = VOLTAGE_SL_RESULT_PATTERN.sub(r"\1  \2", line)

        load_flow_data = self._current_table_description.parse_row(line)
        for data in load_flow_data:
            self._analyse_load_flow_data(data)
