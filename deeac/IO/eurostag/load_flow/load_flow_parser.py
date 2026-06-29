"""
Module for load_flow_parser.

:module: load_flow_parser
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import re

from typing import Dict

import numpy as np

from deeac.Models.network import Network
from deeac.Models.bus import Bus
from deeac.Models.breaker import Breaker
from deeac.Models.line import Line
from deeac.Models.transformer import Transformer
from deeac.enums import ElementType, BusType, TableType
from deeac.IO.eurostag.load_flow.table_description import LOAD_FLOW_TABLE_DELIMITER, TableDescription
from deeac.Models.constants import BASE_POWER



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
        object_type='Transformer',
        data_occurrences=(2, 5)
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
        object_type='TransformerNodeData'
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
        object_type='TransformerTapData'
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
        object_type='HVDCConverter'
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
        object_type='Result'
    )
}


# Description of the table of interest in the file

class EurostagLoadFlowParser:
    """
    Eurostagloadflowparser.
    
    Rationale:
        This class handles input parsing or configuration shaping. It converts
        external data into the explicit objects consumed by the EEAC pipeline.
    
    :ivar load_flow_results_file: load flow results file.
    :ivar load_flow_input_file: load flow input file.
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

        # Network topology where load flow values are loaded
        self._network = None

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

        # Exception collector placeholder (list of exceptions if needed)
        self._exception_collector = []


        # Generate element types only once to increase performances
        self._elements_types = {}
        for tpe in ElementType:
            self._elements_types[tpe.value] = tpe

        self._divergence_error = "ERR-019.0461"
        self._page_number_removal = str.maketrans('0123456789', '          ')

    def _reset_parser(self):
        """
        reset parser.
        
        :return: Return value.
        """
        self._transformer_info.clear()
        self._current_origin_node_name = None
        self._exception_collector = []
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
        run load flow.
        
        :return: Return value.
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
            raise ValueError(f"Duplicate {object_type} name: {name}")

    # def _raise_validation_errors(self, e: ValidationError, load_flow_data: estgdtos_LoadFlowData):
    #
    """
    #     Raise an ExceptionList with validation errors raised when trying to map load flow data to a Pydantic model.
    #
    #     :param e: Validation error to raise.
    #     :param load_flow_data: LoadFlowData at the origin of the error.
    #     :raise ExceptionList with the errors.
    #
    """
    #     exception_list = DEEACExceptionList([])
    #     # Get validation errors and create corresponding DEEAC exceptions
    #     for val_error in e.errors():
    #         exception_list.append(
    #             LoadFlowDataValidationException(load_flow_data.dict(), val_error["loc"], val_error["type"])
    #         )
    #     raise (exception_list)

    def _analyse_load_flow_data(self, load_flow_data: dict, object_type: str):
        """
        Analyse load flow data to extract data of interest.
        
        :param load_flow_data: Load flow data to analyse.
        """
        if object_type == 'Transformer':
            # Extract transformer node names, only for detailed transformers
            if load_flow_data['type'] == '8':

                self._transformer_info.append((
                    load_flow_data['sending_node'],
                    load_flow_data['receiving_node'],
                    load_flow_data['parallel_index']
                ))
        elif object_type == 'TransformerNodeData':
            if load_flow_data.get('orig_node', None) is not None:
                if load_flow_data['orig_zone'] in ("GE", "LO", "CA", "SV"):
                    return
                # self._raise_if_duplicated(load_flow_data['orig_node'], self._transformer_nodes_data,
                #                           TransformerNodeData.__name__) TODO: Check possible alternative implemenation
                self._transformer_nodes.append(f"{load_flow_data['orig_zone']}_{load_flow_data['orig_node']}")
                self._transformer_nodes_data[load_flow_data['orig_node']] = {
                    'orig_node':load_flow_data['orig_node'],
                    'zone':load_flow_data['orig_zone'],
                    'parallel_ids':list(),
                    'types':list(),
                    'nodes':list(),
                    'resistances':list(),
                    'reactances':list(),
                    'shunt_susceptances':list(),
                    'shunt_conductances':list()
                }

            elif load_flow_data['type'] not in ('1', '8'):
                return

            else:
                orig_zone, orig_node = self._transformer_nodes[-1].split("_", 1)
                # if load_flow_data.zone in ("GE", "LO", "CA", "SV"):
                #     return
                #
                # if orig_zone != load_flow_data.zone:
                #     raise ValueError(f"Zone incoherence for {load_flow_data.orig_node} in load flow data")

                self._transformer_nodes_data[orig_node]['parallel_ids'].append(load_flow_data['parallel_index'])
                self._transformer_nodes_data[orig_node]['types'].append(load_flow_data['type'])
                self._transformer_nodes_data[orig_node]['nodes'].append(load_flow_data['node'])
                self._transformer_nodes_data[orig_node]['resistances'].append(float(load_flow_data['resistance']))
                self._transformer_nodes_data[orig_node]['reactances'].append(float(load_flow_data['reactance']))
                self._transformer_nodes_data[orig_node]['shunt_susceptances'].append(float(load_flow_data['shunt_susceptance']))
                self._transformer_nodes_data[orig_node]['shunt_conductances'].append(float(load_flow_data['shunt_conductance']))

        elif object_type == 'TransformerTapData':
            if load_flow_data.get('sending_node', None) is not None:
                tap_name = f"{load_flow_data['receiving_node']}_{load_flow_data['sending_node']}_{load_flow_data['parallel_index']}"
                self._transformer_taps.append(tap_name)
                self._transformer_tap_data[tap_name] = {
                    'sending_node':load_flow_data['sending_node'],
                    'receiving_node':load_flow_data['receiving_node'],
                    'tap_numbers':list(),
                    'phase_angles':list(),
                    'sending_node_voltages':list(),
                    'receiving_node_voltages':list()
                }
            else:
                tap_name = self._transformer_taps[-1]
                self._transformer_tap_data[tap_name]['tap_numbers'].append(int(load_flow_data['tap_number']))
                self._transformer_tap_data[tap_name]['phase_angles'].append(float(load_flow_data['phase_angle']))
                self._transformer_tap_data[tap_name]['sending_node_voltages'].append(
                    float(load_flow_data['sending_node_voltage']))
                self._transformer_tap_data[tap_name]['receiving_node_voltages'].append(
                    float(load_flow_data['receiving_node_voltage']))

        elif object_type == 'HVDCConverter':

            # High voltage direct current converter
            #self._raise_if_duplicated(load_flow_data['converter_name'], self._hvdc_converters, HVDCConverter.__name__) TODO: Check possible alternative implemenation
            # try:

            hvdc_converter = self._network.hvdc_map.get(load_flow_data['converter_name'], None)

            if hvdc_converter is not None:
                bus = self._network.bus_map.get(hvdc_converter.bus.name, None)

                hvdc_converter.active_power = - float(load_flow_data['active_power'])
                hvdc_converter.reactive_power = - float(load_flow_data['reactive_power'])

                hvdc_converter.compute_admittance()
                bus.add_load(hvdc_converter)

            else:
                raise KeyError(f"HVDC converter {load_flow_data['converter_name']} not found in topology.")

        elif object_type == 'Result':
            # Get element type
            if load_flow_data.get('area', None) in self._elements_types:
                element_type = self._elements_types[load_flow_data['area']]
            else:
                # Element is unknown
                element_type = None

            if element_type is None and load_flow_data.get('node_name', None) is not None:
                # Data associated to a bus
                # self._raise_if_duplicated(load_flow_data['node_name'], self._buses, BusLF.__name__)
                if load_flow_data['voltage'] == 0:
                    # Skip if voltage is 0 (probably disconnected)
                    return
                # try:
                self._buses[load_flow_data['node_name']] = {
                    'name': load_flow_data['node_name'],
                    'voltage': float(load_flow_data['voltage']),
                    'phase_angle': float(load_flow_data['phase_angle'])
                }
                # except ValidationError as e:
                #     self._raise_validation_errors(e, load_flow_data)
                # Update current origin node name
                self._current_origin_node_name = load_flow_data['node_name']

            elif element_type == ElementType.GENERATOR:
                # Data associated to a PV generator
                # self._raise_if_duplicated(load_flow_data['node_name'], self._generators, GeneratorLF.__name__)
                # try:

                generator = self._network.generator_map.get(load_flow_data['node_name'], None)
                if generator is not None:
                    bus = self._network.bus_map.get(generator.bus.name, None)
                    generator.active_power = float(load_flow_data['production_active_power'])
                    generator.reactive_power = float(load_flow_data['production_reactive_power'])

                    # Convert inertia constant to system-based
                    generator.inertia_constant /= BASE_POWER  # TODO: Double check base power here
                    # Minimum and maximum powers

                    # Create generator model and connect it to its bus
                    generator.compute_internal_voltage()
                    bus.add_generator(generator)
                else:
                    load = self._network.load_map.get(f"GEN_{load_flow_data['node_name']}", None)
                    if load is not None:
                        bus = self._network.bus_map.get(load.bus.name, None)
                        load.active_power = -1 * float(load_flow_data['production_active_power'])
                        load.reactive_power = -1 * float(load_flow_data['production_reactive_power'])
                        load.compute_admittance()
                        bus.add_load(load)
                    else:
                        raise KeyError(
                            f"Generator {load_flow_data['node_name']} not found neither in gens or loads."
                        )

                # except ValidationError as e:
                #     self._raise_validation_errors(e, load_flow_data)

            elif element_type == ElementType.LOAD:
                # Data associated to a PV load
                # self._raise_if_duplicated(load_flow_data.node_name, self._loads, Load.__name__)
                # try:

                load = self._network.load_map.get(load_flow_data['node_name'].upper(), None)
                if load is not None:
                    bus = self._network.bus_map.get(load.bus.name, None)

                    load.active_power = float(load_flow_data['load_active_power'])
                    load.reactive_power = float(load_flow_data['load_reactive_power'])

                    load.compute_admittance()
                    bus.add_load(load)

                else:
                    print('')
                    pass
                    # raise KeyError(f'Load {load_flow_data['node_name']} not found in topology.')

                # except ValidationError as e:
                #     self._raise_validation_errors(e, load_flow_data)

            elif element_type == ElementType.SVC:
                # Data associated to a static var compensator
                # self._raise_if_duplicated(
                #     load_flow_data.node_name,
                #     self._static_var_compensators,
                #     StaticVarCompensator.__name__
                # )

                svc = self._network.svc_map.get(load_flow_data['node_name'], None)

                if svc is not None:
                    bus = self._network.bus_map.get(svc.bus.name, None)
                    svc.reactive_power = - float(load_flow_data['production_reactive_power'])

                    # Get bus connected to converter
                    svc.compute_admittance()
                    bus.add_capacitor_bank(svc)

                else:
                    raise KeyError(f"SVC {load_flow_data['node_name']} not found in topology.")


            elif load_flow_data.get('node_name', None) is None:
                # Data associated to a branch, get origin node
                if self._current_origin_node_name is None:
                    raise ValueError(load_flow_data['connected_node_name'])
                connected_node_name = load_flow_data['connected_node_name']
                tfo_id = (self._current_origin_node_name, connected_node_name, load_flow_data['branch_parallel_index'])
                if tfo_id not in self._transformer_info:
                    # Branch must not be considered
                    return
                if tfo_id in self._transformers:
                    # This parallel transformer was already observed
                    raise ValueError(
                        self._current_origin_node_name, connected_node_name, load_flow_data['branch_parallel_index']
                    )
                # try:
                self._transformers[tfo_id] = {
                    'sending_bus': self._current_origin_node_name,
                    'receiving_bus': load_flow_data['connected_node_name'],
                    'parallel_id': load_flow_data['branch_parallel_index'],
                    'tap_number': int(load_flow_data['transformer_tap'])
                }
                # except ValidationError as e:
                #     self._raise_validation_errors(e, load_flow_data)

    def parse_load_flow(self, network: Network) -> None:
        """
        Parse the results of the load flow analysis and apply them to the network.
        
        :param network: Network to update.
        """
        self._reset_parser()
        self._network = network

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
        # self._exception_collector.raise_for_exception()

        # Update bus voltages and angles.
        for bus in network.buses:
            load_flow_bus = self._buses.get(bus.name, None)
            if load_flow_bus is None:
                if bus.type == BusType.SLACK:
                    raise ValueError(bus.name, Bus.__name__)
                # Bus is probably disconnected.
                bus.voltage_magnitude = 0
                bus.phase_angle = 0
            else:
                if bus.type == BusType.SLACK:
                    bus.voltage_magnitude = load_flow_bus['voltage']
                else:
                    bus.voltage_magnitude = load_flow_bus['voltage']
                    bus.phase_angle = np.deg2rad(load_flow_bus['phase_angle'])

        # Capacitor banks are static, compute admittances after voltages are set.
        for bank in network.capacitor_banks:
            bank.compute_admittance()
            bank.bus.add_capacitor_bank(bank)

        # Build breaker list and finalize branch elements.
        network.clear_breakers()
        for branch in network.branches:
            branch_type = type(next(iter(branch.parallel_elements.values())))
            if branch_type == Breaker:
                network.breakers.append(branch)
                continue

            # Ensure the branch is attached to buses.
            branch.first_bus.add_branch(branch)
            branch.second_bus.add_branch(branch)

            for parallel_id, element in branch.parallel_elements.items():
                element_type = type(element)
                if element_type == Breaker:
                    branch[parallel_id] = element
                    continue

                if element_type == Line:
                    sending_bus_base_voltage = branch.first_bus.base_voltage
                    receiving_bus_base_voltage = branch.second_bus.base_voltage
                    element.base_impedance = (
                        sending_bus_base_voltage * receiving_bus_base_voltage / BASE_POWER
                    )
                    branch[parallel_id] = element
                    continue

                if element_type == Transformer:
                    if element.closed_at_first_bus is False or element.closed_at_second_bus is False:
                        continue

                    if element.transformer_type == 8:
                        tap_data = self._transformer_tap_data.get(
                            f"{branch.first_bus.name}_{branch.second_bus.name}_{parallel_id}", None
                        )
                        if tap_data is None:
                            tap_data = self._transformer_tap_data.get(
                                f"{branch.second_bus.name}_{branch.first_bus.name}_{parallel_id}", None
                            )
                        if tap_data is None:
                            raise ValueError(
                                f"{branch.first_bus.name}_{branch.second_bus.name}",
                                "transformer_tap_data",
                            )

                        tap_index = tap_data['tap_numbers'].index(element.initial_tap_number)
                        sending_node_voltage = tap_data['sending_node_voltages'][tap_index]
                        receiving_node_voltage = tap_data['receiving_node_voltages'][tap_index]
                        element.ratio = (
                            branch.first_bus.base_voltage / sending_node_voltage
                        ) * (receiving_node_voltage / branch.second_bus.base_voltage)
                        phase_shift_angle_deg = tap_data['phase_angles'][tap_index]
                        element.phase_shift_angle = np.deg2rad(phase_shift_angle_deg)

                    first_node_data = self._transformer_nodes_data[branch.first_bus.name]
                    second_node_data = self._transformer_nodes_data[branch.second_bus.name]
                    second_bus_indices = [
                        i for i, node in enumerate(first_node_data['nodes'])
                        if node == branch.second_bus.name and first_node_data['parallel_ids'][i] == parallel_id
                    ]
                    first_bus_indices = [
                        i for i, node in enumerate(second_node_data['nodes'])
                        if node == branch.first_bus.name and second_node_data['parallel_ids'][i] == parallel_id
                    ]
                    second_bus_index = second_bus_indices[0]
                    first_bus_index = first_bus_indices[0]

                    resistance = first_node_data['resistances'][second_bus_index]
                    if resistance != second_node_data['resistances'][first_bus_index]:
                        raise ValueError("Resistance error")
                    reactance = first_node_data['reactances'][second_bus_index]
                    if reactance != second_node_data['reactances'][first_bus_index]:
                        raise ValueError("Reactance error")
                    shunt_conductance = first_node_data['shunt_conductances'][second_bus_index]
                    if shunt_conductance != second_node_data['shunt_conductances'][first_bus_index]:
                        raise ValueError("Shunt conductance error")
                    shunt_susceptance = first_node_data['resistances'][second_bus_index]
                    if first_node_data['shunt_susceptances'][second_bus_index] != (
                        second_node_data['shunt_susceptances'][first_bus_index]
                    ):
                        raise ValueError("Shunt susceptance error")

                    element.resistance = float(resistance) * element.base_impedance
                    element.reactance = float(reactance) * element.base_impedance
                    element.shunt_conductance = float(shunt_conductance) / element.base_impedance
                    element.shunt_susceptance = float(shunt_susceptance) / element.base_impedance
                    branch[parallel_id] = element
                    continue

                raise ValueError(branch.first_bus.name, branch.second_bus.name)

    def _parse_line(self, line: str) -> None:
        """
        Parses the content of one line of the load flow result file
        :param line: one line of the load flow file to parse
        """
        if self._divergence_error in line:
            raise ValueError("Load flow diverged.")

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
            self._analyse_load_flow_data(data, self._current_table_description.object_type)
