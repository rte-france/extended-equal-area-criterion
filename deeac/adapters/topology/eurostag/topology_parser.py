# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.domain.utils import get_element
from deeac.domain.ports.topology import TopologyParser
from deeac.domain.ports.dtos import Value, Unit
from deeac.domain.ports.dtos.topology import (
    NetworkTopology, Bus, SlackBus, Branch, Line, Transformer1, Transformer8, Breaker, Load, Generator, CapacitorBank,
    StaticVarCompensator, HVDCConverter, ENR
)
from deeac.domain.ports.exceptions import (
    BranchParallelException, NetworkElementNameException, NominalTapException
)
from deeac.domain.exceptions import DEEACExceptionCollector, ElementNotFoundException
from deeac.adapters.topology.eurostag.dtos import State, GeneratorRegulatingMode, OpeningCode, HVDCConverterState
from .exceptions import GeneralParametersException
from .ech_file_parser import EchEurostagFileParser, EchRecordType
from .dta_file_parser import DtaEurostagFileParser, DtaRecordType


class EurostagTopologyParser(TopologyParser):
    """
    Parser of an Eurostag network topology.
    This topology is obtained from .ech and .dta files.
    """

    def __init__(self, ech_file: str, dta_file: str):
        """
        Initialize the parser with path to .ech and .dta files.

        :param ech_file: Path to the file with static network data.
        :param dta_file: Path to the file with dynamic network data.
        """
        self.ech_file_parser = EchEurostagFileParser(ech_file)
        self.dta_file_parser = DtaEurostagFileParser(dta_file)

    def parse_network_topology(self) -> NetworkTopology:
        """
        Parse Eurostag files to retrieve a network topology.

        :return: An object representing the parsed network topology.
        :raise: DEEACExceptionList if topology could not be parsed.
        """
        exception_collector = DEEACExceptionCollector()

        # Parse ech and dta files
        with exception_collector:
            self.ech_file_parser.parse_file()
        with exception_collector:
            self.dta_file_parser.parse_file()
        exception_collector.raise_for_exception()

        # Base power
        with exception_collector:
            general_parameters_data = self.ech_file_parser.get_network_data(EchRecordType.GENERAL_PARAMETERS)
            if len(general_parameters_data) > 1:
                # Only one record must appear in the ech file.
                raise GeneralParametersException()
            base_power = general_parameters_data[0].base_power
            if base_power is None or base_power == 0:
                # Default value
                base_power = Value(value=100, unit=Unit.MVA)
            else:
                base_power = Value(value=base_power, unit=Unit.MVA)
        # Cannot go further without base power
        exception_collector.raise_for_exception()

        # Buses
        buses = {}
        buses_data = self.ech_file_parser.get_network_data(EchRecordType.NODE)
        slack_buses_data = self.ech_file_parser.get_network_data(EchRecordType.SLACK_BUS)
        slack_buses_data = {slack_bus.name: slack_bus.phase_angle for slack_bus in slack_buses_data}
        slack_buses = list()
        for bus_data in buses_data:
            with exception_collector:
                # Base voltage phase to phase in kV
                base_voltage = Value(value=bus_data.base_voltage, unit=Unit.KV)
                if bus_data.name in buses:
                    # Different buses must have different names
                    raise NetworkElementNameException(bus_data.name, Bus.__name__)

                if bus_data.name in slack_buses_data:
                    phase_angle = Value(value=slack_buses_data[bus_data.name], unit=Unit.DEG)
                    # Slack bus with its phase angle
                    slack_bus = SlackBus(name=bus_data.name, base_voltage=base_voltage, phase_angle=phase_angle)
                    buses[bus_data.name] = slack_bus
                    slack_buses.append(slack_bus)
                else:
                    # Simple bus
                    buses[bus_data.name] = Bus(name=bus_data.name, base_voltage=base_voltage)
        # All buses must be identified before proceeding further
        exception_collector.raise_for_exception()

        # Branches
        branches = {}
        branch_record_types = [
            EchRecordType.LINE,
            EchRecordType.TYPE1_TRANSFORMER,
            EchRecordType.TYPE8_TRANSFORMER,
            EchRecordType.COUPLING_DEVICE
        ]
        for record_type in branch_record_types:
            network_data = self.ech_file_parser.get_network_data(record_type)
            for data in network_data:
                with exception_collector:
                    # Connected buses
                    sending_bus = get_element(data.sending_node, buses, Bus.__name__)
                    receiving_bus = get_element(data.receiving_node, buses, Bus.__name__)
                    connected_bus_names = (sending_bus.name, receiving_bus.name)

                    # Parallel ID
                    parallel_id = data.parallel_index

                    # Lines
                    if record_type == EchRecordType.LINE:
                        # Opening state
                        line_closed_at_sending_bus = False if (
                            data.opening_code in {OpeningCode.SENDING_SIDE_OPEN, OpeningCode.BOTH_SIDE_OPEN}
                        ) else True
                        line_closed_at_receiving_bus = False if (
                            data.opening_code in {OpeningCode.RECEIVING_SIDE_OPEN, OpeningCode.BOTH_SIDE_OPEN}
                        ) else True

                        # Resistance and reactance converted from p.u.
                        # Base power and rated apparent power in MVA both
                        # Base voltage used in Eurostag per unit system is phase to phase
                        base = sending_bus.base_voltage.value * receiving_bus.base_voltage.value / base_power.value
                        line_resistance = data.resistance * base
                        line_reactance = data.reactance * base

                        # Shunt conductance and reactance converted from p.u.
                        # Semi-shunt to shunt implies to multiply by 2.
                        line_shunt_conductance = 2 * data.semi_shunt_conductance / base
                        line_shunt_susceptance = 2 * data.semi_shunt_susceptance / base

                        # Create line element
                        element = Line(
                            closed_at_sending_bus=line_closed_at_sending_bus,
                            closed_at_receiving_bus=line_closed_at_receiving_bus,
                            resistance=Value(value=line_resistance, unit=Unit.OHM),
                            reactance=Value(value=line_reactance, unit=Unit.OHM),
                            shunt_conductance=Value(value=line_shunt_conductance, unit=Unit.S),
                            shunt_susceptance=Value(value=line_shunt_susceptance, unit=Unit.S)
                        )
                    # Type-1 TFO
                    elif record_type == EchRecordType.TYPE1_TRANSFORMER:
                        # Opening state
                        t1_closed_at_sending_bus = False if (
                            data.opening_code in {OpeningCode.SENDING_SIDE_OPEN, OpeningCode.BOTH_SIDE_OPEN}
                        ) else True
                        t1_closed_at_receiving_bus = False if (
                            data.opening_code in {OpeningCode.RECEIVING_SIDE_OPEN, OpeningCode.BOTH_SIDE_OPEN}
                        ) else True

                        # Resistance and reactance converted from p.u.
                        # Base voltage is the one of the receiving node (voltage in kV and base power in MVA)
                        # Base voltage used in Eurostag per unit system is phase to phase : sqrt(3) * Vb
                        base_impedance = receiving_bus.base_voltage.value ** 2 / base_power.value

                        # Create TFO
                        element = Transformer1(
                            sending_node=data.sending_node,
                            receiving_node=data.receiving_node,
                            closed_at_sending_bus=t1_closed_at_sending_bus,
                            closed_at_receiving_bus=t1_closed_at_receiving_bus,
                            base_impedance=Value(value=base_impedance, unit=Unit.OHM),
                            ratio=data.transformation_ratio
                        )
                    # Type-8 TFO
                    elif record_type == EchRecordType.TYPE8_TRANSFORMER:
                        # Opening state
                        t8_closed_at_sending_bus = False if (
                            data.opening_code in {OpeningCode.SENDING_SIDE_OPEN, OpeningCode.BOTH_SIDE_OPEN}
                        ) else True
                        t8_closed_at_receiving_bus = False if (
                            data.opening_code in {OpeningCode.RECEIVING_SIDE_OPEN, OpeningCode.BOTH_SIDE_OPEN}
                        ) else True

                        # Get data associated to nominal tap number to compute base
                        try:
                            nominal_tap = next(tap for tap in data.taps if tap.tap_number == data.nominal_tap_number)
                        except StopIteration:
                            raise NominalTapException(
                                    data.nominal_tap_number, sending_bus.name, receiving_bus.name, parallel_id
                                )
                        # Base impedance is Z = U_nom^2 / S_nom
                        base_impedance = nominal_tap.receiving_side_voltage ** 2 / data.rated_apparent_power

                        # Taps
                        initial_tap_number = data.initial_tap_position
                        for tap in data.taps:
                            if tap.tap_number == initial_tap_number:
                                break
                        else:
                            raise ValueError(f"Initial tap position {initial_tap_number} not found for {record_type}")

                        # Create TFO
                        element = Transformer8(
                            sending_node=data.sending_node,
                            receiving_node=data.receiving_node,
                            closed_at_sending_bus=t8_closed_at_sending_bus,
                            closed_at_receiving_bus=t8_closed_at_receiving_bus,
                            base_impedance=Value(value=base_impedance, unit=Unit.OHM),
                            initial_tap_number=initial_tap_number,
                            phase_shift_angle=Value(value=tap.phase_shift_angle, unit=Unit.DEG),
                            primary_base_voltage=Value(value=nominal_tap.receiving_side_voltage, unit=Unit.KV),
                            secondary_base_voltage = Value(value=nominal_tap.sending_side_voltage, unit=Unit.KV)
                        )
                    # Breaker
                    else:
                        # Connection state
                        breaker_closed = True if data.opening_code is None else False

                        # Create Breaker
                        element = Breaker(closed=breaker_closed)

                    # Associate line to its branch (all branches so far are of the type LINE)
                    if connected_bus_names not in branches:
                        # New branch
                        branches[connected_bus_names] = Branch(
                            sending_bus=sending_bus,
                            receiving_bus=receiving_bus
                        )
                    elif parallel_id in branches[connected_bus_names].parallel_elements:
                        # Two elements with same parallel ID
                        raise BranchParallelException(sending_bus.name, receiving_bus.name, parallel_id)
                    branches[connected_bus_names].parallel_elements[parallel_id] = element

        # Loads
        loads = {}
        loads_data = self.ech_file_parser.get_network_data(EchRecordType.LOAD)
        for load_data in loads_data:
            with exception_collector:
                if load_data.name in loads:
                    # Distinct loads should have different names
                    raise NetworkElementNameException(load_data.name, Load.__name__)

                # Connected bus
                connected_bus = get_element(load_data.bus_name, buses, Bus.__name__)

                # Connected state
                load_connected = True if load_data.state == State.CONNECTED else False

                # Create load
                load = Load(
                    name=load_data.name,
                    bus=connected_bus,
                    connected=load_connected,
                    active_power=Value(value=load_data.active_power, unit=Unit.MW),
                    reactive_power=Value(value=load_data.reactive_power, unit=Unit.MVAR)
                )
                loads[load.name] = load

        # Generators
        generator_dicts = {}
        generators_dynamic_data = self.dta_file_parser.get_network_data(DtaRecordType.FULL_EXTERNAL_PARAM_GENERATOR)
        for generator_data in generators_dynamic_data:
            with exception_collector:
                # Name
                generator_content = {"name": generator_data.name}

                # Compute base for per-unit conversions
                rated_apparent_power = generator_data.rated_apparent_power
                base = generator_data.base_voltage_machine_side ** 2 / rated_apparent_power

                # Direct transient reactance
                direct_transient_reactance = generator_data.direct_transient_reactance * base
                generator_content["direct_transient_reactance"] = Value(value=direct_transient_reactance, unit=Unit.OHM)

                # Inertia constant (converted from device-based system)
                generator_content["inertia_constant"] = Value(
                    value=generator_data.inertia_constant * rated_apparent_power,
                    unit=Unit.MWS_PER_MVA
                )

                # Store the data that was read
                generator_dicts[generator_data.name] = generator_content

        generators = []
        generator_names = set()
        generators_static_data = self.ech_file_parser.get_network_data(EchRecordType.GENERATOR)
        for generator_data in generators_static_data:
            with exception_collector:
                # Name
                generator_name = generator_data.name
                if generator_name in generator_names:
                    # Distinct generators should have different names
                    raise NetworkElementNameException(generator_name, Generator.__name__)
                generator_names.add(generator_name)

                # Get dynamic data, if any
                try:
                    generator_content = get_element(generator_name, generator_dicts, Generator.__name__)
                    generator_is_load = False
                except ElementNotFoundException:
                    # Eolian and Photovoltaic generators have no dynamic data and will still be modeled as ENR
                    if generator_data.source=="Eolien" or generator_data.source=="Photovol":
                        continue
                    else:
                        # Other generators have no dynamic data and will be modeled as loads
                        generator_name = f"GEN_{generator_name}"
                        if generator_name in loads:
                            # Distinct loads should have different names
                            raise NetworkElementNameException(generator_name, Load.__name__)
                        generator_content = {"name": generator_name}
                        generator_is_load = True

                # Connected bus
                connected_bus = get_element(generator_data.bus_name, buses, Bus.__name__)
                generator_content["bus"] = connected_bus

                # Connection state
                generator_content["connected"] = True if generator_data.state == State.CONNECTED else False

                # Active power (P)
                generator_active_power = generator_data.active_power
                if generator_active_power is not None:
                    generator_active_power = Value(value=generator_active_power, unit=Unit.MW)
                generator_content["active_power"] = generator_active_power
                generator_max_active_power = generator_data.max_active_power
                generator_content["max_active_power"] = Value(value=generator_max_active_power, unit=Unit.MW)
                # Reactive power (Q)
                generator_reactive_power = generator_data.reactive_power
                if generator_reactive_power is not None:
                    generator_reactive_power = Value(value=generator_reactive_power, unit=Unit.MVAR)
                generator_content["reactive_power"] = generator_reactive_power

                #generator_source = Generator
                generator_content["source"] = generator_data.source

                if generator_is_load:
                    # Generator is modeled as a negative load
                    generator_active_power.value *= -1
                    generator_reactive_power.value *= -1
                    loads[generator_name] = Load(**generator_content)
                    continue

                # Regulating mode
                generator_content["regulating"] = True \
                    if generator_data.regulating_mode == GeneratorRegulatingMode.REGULATING else False

                # Create generator
                generators.append(Generator(**generator_content))

        # ENR
        enr = []
        enr_names = set()
        enr_static_data = self.ech_file_parser.get_network_data(EchRecordType.GENERATOR)
        for enr_data in enr_static_data:
            with exception_collector:
                if enr_data.source=="Eolien" or enr_data.source=="Photovol":
                    # Name
                    enr_name = enr_data.name
                    if enr_name in enr_names:
                        # Distinct enr should have different names
                        raise NetworkElementNameException(enr_name, ENR.__name__)
                    enr_names.add(enr_name)
                    enr_content = {"name": enr_name}

                    # Connected bus
                    connected_bus = get_element(enr_data.bus_name, buses, Bus.__name__)
                    enr_content["bus"] = connected_bus

                    # Connection state
                    enr_content["connected"] = True if enr_data.state == State.CONNECTED else False

                    # Active power (P)
                    enr_active_power = enr_data.active_power
                    if enr_active_power is not None:
                        enr_active_power = Value(value=enr_active_power, unit=Unit.MW)
                    enr_content["active_power"] = enr_active_power
                    enr_max_active_power = enr_data.max_active_power
                    enr_content["max_active_power"] = Value(value=enr_max_active_power, unit=Unit.MW)
                    # Reactive power (Q)
                    enr_reactive_power = generator_data.reactive_power
                    if enr_reactive_power is not None:
                        enr_reactive_power = Value(value=enr_reactive_power, unit=Unit.MVAR)
                    enr_content["reactive_power"] = enr_reactive_power

                    #generator_source = Generator
                    enr_content["source"] = generator_data.source

                    # Regulating mode
                    enr_content["regulating"] = True \
                        if enr_data.regulating_mode == GeneratorRegulatingMode.REGULATING else False

                    # Create enr
                    enr.append(ENR(**enr_content))

                else:
                    continue

        # Capacitor banks
        capacitor_banks = {}
        capacitor_banks_data = self.ech_file_parser.get_network_data(EchRecordType.CAPACITOR_BANK)
        for capacitor_bank_data in capacitor_banks_data:
            with exception_collector:
                if capacitor_bank_data.name in capacitor_banks:
                    # Distinct capacitor banks should have different names
                    raise NetworkElementNameException(capacitor_bank_data.name, CapacitorBank.__name__)

                # Connected bus
                connected_bus = get_element(capacitor_bank_data.bus_name, buses, Bus.__name__)

                # Get number of steps, losses and reactive power
                nb_steps = capacitor_bank_data.number_active_steps
                loss_on_step = capacitor_bank_data.active_loss_on_step
                reactive_power_on_step = capacitor_bank_data.reactive_power_on_step

                # Compute active and reactive powers (losses are in kW and converted in MW)
                active_power = nb_steps * loss_on_step / 1000
                reactive_power = nb_steps * reactive_power_on_step

                # Create capacitor bank
                capacitor_bank = CapacitorBank(
                    name=capacitor_bank_data.name,
                    bus=connected_bus,
                    active_power=Value(value=active_power, unit=Unit.MW),
                    reactive_power=Value(value=reactive_power, unit=Unit.MVAR)
                )
                capacitor_banks[capacitor_bank.name] = capacitor_bank

        # SVCs
        svcs = {}
        svcs_data = self.ech_file_parser.get_network_data(EchRecordType.SVC)
        for svc_data in svcs_data:
            with exception_collector:
                if svc_data.name in svcs:
                    # Distinct SVCs should have different names
                    raise NetworkElementNameException(svc_data.name, StaticVarCompensator.__name__)

                # Connected bus
                connected_bus = get_element(svc_data.bus_name, buses, Bus.__name__)

                # Connection state
                svc_connected = True if svc_data.state == State.CONNECTED else False

                # Create SVC
                svc = StaticVarCompensator(
                    name=svc_data.name,
                    bus=connected_bus,
                    connected=svc_connected
                )
                svcs[svc.name] = svc

        # HVDC converters
        hvdc_converters = {}
        hvdc_csc_converters_data = self.ech_file_parser.get_network_data(EchRecordType.HVDC_CSC_CONVERTER)
        hvdc_vsc_converters_data = self.ech_file_parser.get_network_data(EchRecordType.HVDC_VSC_CONVERTER)
        hvdc_converters_data = hvdc_csc_converters_data + hvdc_vsc_converters_data
        for hvdc_data in hvdc_converters_data:
            with exception_collector:
                if hvdc_data.name in hvdc_converters:
                    # Distinct converters should have different names
                    raise NetworkElementNameException(hvdc_data.name, HVDCConverter.__name__)

                # Connected bus
                connected_bus = get_element(hvdc_data.bus_name, buses, Bus.__name__)

                # Connection state
                converter_connected = False if hvdc_data.state == HVDCConverterState.OFF else True

                # Create converter
                converter = HVDCConverter(
                    name=hvdc_data.name,
                    bus=connected_bus,
                    connected=converter_connected
                )
                hvdc_converters[converter.name] = converter

        # Raise exceptions if any
        exception_collector.raise_for_exception()

        # Generate network topology
        return NetworkTopology(
            base_power=base_power,
            buses=list(buses.values()),
            slack_buses=slack_buses,
            branches=list(branches.values()),
            loads=list(loads.values()),
            generators=generators,
            enr = enr,
            capacitor_banks=list(capacitor_banks.values()),
            static_var_compensators=list(svcs.values()),
            hvdc_converters=list(hvdc_converters.values())
        )
