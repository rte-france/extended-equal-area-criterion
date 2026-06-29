"""
Module for topology_parser.

:module: topology_parser
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.Models.network import Network

from deeac.enums import BusType, parse_generator_source
from deeac.Models.bus import Bus
from deeac.Models.load import Load
from deeac.Models.line import Line
from deeac.Models.generator import Generator, GeneratorType
from deeac.Models.transformer import Transformer
from deeac.Models.capacitor_bank import CapacitorBank
from deeac.Models.breaker import Breaker
from deeac.IO.eurostag.topology.ech_file_parser import EchEurostagFileParser, EchRecordType
from deeac.IO.eurostag.topology.dta_file_parser import DtaEurostagFileParser, DtaRecordType


class EurostagTopologyParser:
    """
    Eurostagtopologyparser.
    
    Rationale:
        This class handles input parsing or configuration shaping. It converts
        external data into the explicit objects consumed by the EEAC pipeline.
    
    :ivar ech_file_parser: ech file parser.
    :ivar dta_file_parser: dta file parser.
    """

    def __init__(self, ech_file: str, dta_file: str):
        """
        Initialize the parser with path to .ech and .dta files.
        
        :param ech_file: Path to the file with static network data.
        :param dta_file: Path to the file with dynamic network data.
        """
        self.ech_file_parser = EchEurostagFileParser(ech_file)
        self.dta_file_parser = DtaEurostagFileParser(dta_file)

    def parse_network_topology(self) -> Network:
        """
        Parse Eurostag files to retrieve a network topology.
        
        :return: An object representing the parsed network topology.
        :raise: DEEACExceptionList if topology could not be parsed.
        """
        grid = Network(base_power=100.0)

        # Parse ech and dta files
        self.ech_file_parser.parse_file()
        self.dta_file_parser.parse_file()

        # Base power
        general_parameters_data = self.ech_file_parser.get_network_data(EchRecordType.GENERAL_PARAMETERS)
        if len(general_parameters_data) > 1:
            # Only one record must appear in the ech file.
            raise ValueError()
        base_power = float(general_parameters_data[0]['base_power'])
        if base_power is None or base_power == 0:
            # Default value
            base_power = 100
        else:
            base_power = base_power
        grid.base_power = base_power

        # Buses
        buses_data = self.ech_file_parser.get_network_data(EchRecordType.NODE)
        slack_buses_data = self.ech_file_parser.get_network_data(EchRecordType.SLACK_BUS)
        slack_buses_data = {slack_bus['name']: float(slack_bus['phase_angle']) for slack_bus in slack_buses_data}

        for bus_data in buses_data:

            if bus_data['name'] in slack_buses_data:
                phase_angle = slack_buses_data[bus_data['name']]
                # Slack bus with its phase angle
                grid.add_bus(
                    Bus(
                        name=bus_data['name'],
                        base_voltage=float(bus_data['base_voltage']),
                        phase_angle=phase_angle,
                        tpe=BusType.SLACK,
                    )
                )
            else:
                # Simple bus
                grid.add_bus(
                    Bus(name=bus_data['name'], base_voltage=float(bus_data['base_voltage']))
                )

        # Branches
        for record_type in [EchRecordType.LINE,
                            EchRecordType.TYPE1_TRANSFORMER,
                            EchRecordType.TYPE8_TRANSFORMER,
                            EchRecordType.COUPLING_DEVICE]:

            network_data = self.ech_file_parser.get_network_data(record_type)

            for data in network_data:

                # Connected buses
                sending_bus = grid.get_bus_exact(data['sending_node'])
                receiving_bus = grid.get_bus_exact(data['receiving_node'])

                # Parallel ID
                parallel_id = data['parallel_index']

                # Lines
                if record_type == EchRecordType.LINE:
                    # Opening state
                    line_closed_at_sending_bus = False if (
                            data['opening_code'] in {'>', '-'}
                    ) else True
                    line_closed_at_receiving_bus = False if (
                            data['opening_code'] in {'<', '-'}
                    ) else True

                    # Resistance and reactance converted from p.u.
                    # Base power and rated apparent power in MVA both
                    # Base voltage used in Eurostag per unit system is phase to phase
                    base = sending_bus.base_voltage * receiving_bus.base_voltage / base_power
                    line_resistance = float(data['resistance']) * base
                    line_reactance = float(data['reactance']) * base

                    # Shunt conductance and reactance converted from p.u.
                    # Semi-shunt to shunt implies to multiply by 2.
                    line_shunt_conductance = 2 * float(data['semi_shunt_conductance']) / base
                    line_shunt_susceptance = 2 * float(data['semi_shunt_susceptance']) / base

                    # Create line element
                    element = Line(
                        closed_at_first_bus=line_closed_at_sending_bus,
                        closed_at_second_bus=line_closed_at_receiving_bus,
                        resistance=line_resistance,
                        reactance=line_reactance,
                        shunt_conductance=line_shunt_conductance,
                        shunt_susceptance=line_shunt_susceptance,
                        base_impedance=base,
                    )
                # Type-1 TFO

                elif record_type in (EchRecordType.TYPE1_TRANSFORMER, EchRecordType.TYPE8_TRANSFORMER):

                    # Opening state
                    closed_at_sending_bus = False if (
                            data['opening_code'] in {'>', '-'}
                    ) else True
                    closed_at_receiving_bus = False if (
                            data['opening_code'] in {'<', '-'}
                    ) else True

                    # Keep partially opened transformers in the network model.
                    # They do not contribute to the simplified electrical graph
                    # because ``element.closed`` stays false, but the branch must
                    # still exist so that sequence-file mitigation events can
                    # target the already-open side explicitly.

                    if record_type == EchRecordType.TYPE8_TRANSFORMER:

                        # Get data associated to nominal tap number to compute base
                        try:
                            nominal_tap = next(
                                tap for tap in data['taps'] if
                                int(tap['tap_number']) == int(data['nominal_tap_number']))
                        except StopIteration:
                            raise ValueError(
                                int(data['nominal_tap_number']), sending_bus.name, receiving_bus.name, parallel_id
                            )

                        # Taps
                        initial_tap_number = int(data['initial_tap_position'])
                        for tap in data['taps']:
                            if int(tap['tap_number']) == initial_tap_number:
                                break
                        else:
                            raise ValueError(
                                f"Initial tap position {initial_tap_number} not found for {record_type}")

                        transformer_type = 8
                        ratio = None

                        # Taps
                        initial_tap_number = int(data['initial_tap_position'])
                        for tap in data['taps']:
                            if int(tap['tap_number']) == initial_tap_number:
                                break
                        else:
                            raise ValueError(
                                f"Initial tap position {initial_tap_number} not found for {record_type}")

                    else:
                        initial_tap_number = None
                        transformer_type = 1
                        ratio = float(data['transformation_ratio'])

                    base_impedance = receiving_bus.base_voltage ** 2 / base_power

                    element = Transformer(
                        base_impedance=base_impedance,
                        ratio=ratio,
                        sending_node=data['sending_node'],
                        receiving_node=data['receiving_node'],
                        closed_at_first_bus=closed_at_sending_bus,
                        closed_at_second_bus=closed_at_receiving_bus,
                        initial_tap_number=initial_tap_number,
                        transformer_type=transformer_type
                    )

                # Breaker
                else:
                    # Connection state
                    breaker_closed = True if data['opening_code'] is None else False

                    # Create Breaker
                    element = Breaker(closed=breaker_closed)

                grid.add_branch(sending_bus, receiving_bus, element, parallel_id)

        # Loads
        loads_data = self.ech_file_parser.get_network_data(EchRecordType.LOAD)
        for load_data in loads_data:

            # Connected bus
            connected_bus = grid.get_bus_exact(load_data['bus_name'])

            # Connected state
            load_connected = True if load_data['state'] == 'Y' else False  # TODO: Check the State param

            if load_data['name'][:4] == 'GEN_':
                active_power = -1 * float(load_data['active_power'])
                reactive_power = -1 * float(load_data['reactive_power'])
            else:
                active_power = float(load_data['active_power'])
                reactive_power = float(load_data['reactive_power'])

            # Create load
            load = Load(
                name=load_data['name'].upper(),
                bus=connected_bus,
                connected=load_connected,
                active_power=active_power,
                reactive_power=reactive_power
            )
            # loads[load.name] = load
            grid.add_load(load)

        # Generators dynamic data
        generator_dyn_data_dict = dict()
        generators_dynamic_data = self.dta_file_parser.get_network_data(DtaRecordType.FULL_EXTERNAL_PARAM_GENERATOR)
        for generator_data in generators_dynamic_data:
            # Compute base for per-unit conversions
            name = generator_data['name']
            rated_apparent_power = float(generator_data['rated_apparent_power'])
            base = float(generator_data['base_voltage_machine_side']) ** 2 / rated_apparent_power
            xt = float(generator_data['direct_transient_reactance'])
            H = float(generator_data['inertia_constant'])

            # Store the data that was read
            generator_dyn_data_dict[name] = {
                "name": name,
                "direct_transient_reactance": xt * base,
                "inertia_constant": H * rated_apparent_power,
            }

        # generators
        generators_static_data = self.ech_file_parser.get_network_data(EchRecordType.GENERATOR)
        for generator_data in generators_static_data:

            # Name
            generator_name = generator_data['name']

            # Connected bus
            connected_bus = grid.get_bus(generator_data['bus_name'])

            # Connection state
            connected = True if generator_data['state'] == 'Y' else False

            P = float(generator_data['active_power'])
            Pmax = float(generator_data['max_active_power'])
            Q = float(generator_data['reactive_power'])

            # Get dynamic data, if any
            generator_content = generator_dyn_data_dict.get(generator_name, None)
            if generator_content is None:

                # Generator has no dynamic data and will be modeled as a load
                generator_name = f"GEN_{generator_name}"
                grid.check_load_name(generator_name)
                generator_content = {"name": generator_name}

                # Generator is modeled as a negative load
                load = Load(
                    name=generator_content['name'],
                    bus=connected_bus,
                    connected=connected,
                    active_power=-P,
                    reactive_power=-Q
                )
                grid.add_load(load)

            else:

                source = parse_generator_source(generator_data['source'])

                # Regulating mode
                regulating = True if generator_data['regulating_mode'] == 'V' else False

                if connected_bus.type == BusType.SLACK:
                    generator_type = GeneratorType.SLACK
                else:
                    generator_type = GeneratorType.PV if regulating else GeneratorType.PQ

                # Create generator
                grid.add_generator(Generator(
                    name=generator_content['name'],
                    bus=connected_bus,
                    connected=connected,
                    active_power=P,
                    max_active_power=Pmax,
                    reactive_power=Q,
                    direct_transient_reactance=generator_content['direct_transient_reactance'],
                    inertia_constant=generator_content['inertia_constant'],
                    regulating=regulating,
                    tpe=generator_type,
                    source=source,
                ))

        # Capacitor banks
        capacitor_banks_data = self.ech_file_parser.get_network_data(EchRecordType.CAPACITOR_BANK)
        for capacitor_bank_data in capacitor_banks_data:
            # Connected bus
            connected_bus = grid.get_bus_exact(capacitor_bank_data['bus_name'])

            # Get number of steps, losses and reactive power
            nb_steps = int(capacitor_bank_data['number_active_steps'])
            loss_on_step = float(capacitor_bank_data['active_loss_on_step'])
            reactive_power_on_step = float(capacitor_bank_data['reactive_power_on_step'])

            # Compute active and reactive powers (losses are in kW and converted in MW)
            active_power = nb_steps * loss_on_step / 1000
            reactive_power = - nb_steps * reactive_power_on_step

            # Create capacitor bank
            capacitor_bank = CapacitorBank(
                name=capacitor_bank_data['name'],
                bus=connected_bus,
                active_power=active_power,
                reactive_power=reactive_power
            )
            # capacitor_banks[capacitor_bank.name] = capacitor_bank
            grid.add_capacitor_bank(capacitor_bank)

        # SVCs
        svcs_data = self.ech_file_parser.get_network_data(EchRecordType.SVC)
        for svc_data in svcs_data:
            # Connected bus
            connected_bus = grid.get_bus_exact(svc_data['bus_name'])

            # Connection state
            svc_connected = True if svc_data['state'] == 'Y' else False

            # Create SVC
            svc = CapacitorBank(
                name=svc_data['name'],
                bus=connected_bus,
                connected=svc_connected,
                active_power=0,
                reactive_power=0
            )
            # svcs[svc.name] = svc
            grid.add_static_var_compensator(svc)

        # HVDC converters
        hvdc_csc_converters_data = self.ech_file_parser.get_network_data(EchRecordType.HVDC_CSC_CONVERTER)
        hvdc_vsc_converters_data = self.ech_file_parser.get_network_data(EchRecordType.HVDC_VSC_CONVERTER)
        hvdc_converters_data = hvdc_csc_converters_data + hvdc_vsc_converters_data
        for hvdc_data in hvdc_converters_data:
            # Connected bus
            connected_bus = grid.get_bus_exact(hvdc_data['bus_name'])

            # Connection state
            converter_connected = False if hvdc_data['state'] == 'S' else True

            # Create converter
            converter = Load(
                name=hvdc_data['name'],
                bus=connected_bus,
                active_power=0,
                reactive_power=0,
                connected=converter_connected
            )
            # hvdc_converters[converter.name] = converter
            grid.add_hvdc_converter(converter)

        return grid
