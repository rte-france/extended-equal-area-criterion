# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0f
# This file is part of the deeac project.

from cmath import phase, pi
from functools import lru_cache

import networkx as nx
from typing import List, Set, Tuple, DefaultDict, TYPE_CHECKING
from enum import Enum
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from deeac.domain.utils import get_element, deepcopy
from deeac.domain.ports.dtos import topology as topology_dtos, load_flow as load_flow_dtos
from deeac.domain.exceptions import (
    DEEACExceptionCollector, BranchContentException, LoadFlowException, ElementNotFoundException, ParallelException,
    SimplifiedNetworkBreakerExcepion, NetworkStateException, MultipleSlackBusException, NoSlackBusException
)
from .bus import Bus, BusType
from .branch import Branch
from .breaker import Breaker, ParallelBreakers
from .capacitor_bank import CapacitorBank
from .generator import Generator, GeneratorType, GeneratorSource
from .load import FictiveLoad, Load
from .line import Line
from .transformer import Transformer
from .value import Value, Unit, PUBase
from .matrices import AdmittanceMatrix

if TYPE_CHECKING:
    from .events import Event


class NetworkState(Enum):
    """
    States of a network.
    """
    PRE_FAULT = "PRE_FAULT"
    DURING_FAULT = "DURING_FAULT"
    POST_FAULT = "POST_FAULT"


class Network:
    """
    Distribution network
    """

    def __init__(self, buses: List[Bus], breakers: List[ParallelBreakers], base_power: Value, frequency: float = None):
        """
        Initialize a topology with a list of its buses.

        :param buses: List of the buses in the topology.
        :param breakers: List of the breakers that couple buses in the network.
        :param base_power: System base power.
        :param frequency: Frequency for this network (50Hz in Europe, default value). unit: Hz.
        """
        self.buses = buses
        self._breakers = breakers
        self.base_power = base_power
        if frequency is None:
            self.frequency = 50
        else:
            self.frequency = frequency

        # Events to produce during and post-fault networks
        self._failure_events = []
        self._mitigation_events = []

        # Different simplified versions of the network, with the buses that were discarded in graph analysis
        self._simplified_networks = {
            NetworkState.PRE_FAULT: None,
            NetworkState.DURING_FAULT: None,
            NetworkState.POST_FAULT: None
        }

        # Get generators to avoid expensive operations
        self._generators = [generator for bus in buses for generator in bus.generators]

        # Create bus coupling map
        self._bus_coupling_map = self._build_bus_coupling_map()

        # Results to store
        self._generator_voltage_product_amplitudes = self._compute_generator_voltage_amplitude_product()

        self._admittances = {
            NetworkState.PRE_FAULT: {},
            NetworkState.DURING_FAULT: {},
            NetworkState.POST_FAULT: {}
        }

    def duplicate(self) -> 'Network':
        """
        Duplicate itself without the events and the simplified networks.

        :return: A duplicated version of this network.
        """
        # Backup events and simplified networks
        failure_events = self._failure_events
        mitigation_events = self._mitigation_events
        simplified_networks = self._simplified_networks

        # Empty events and simplified networks to avoid copying them
        self._failure_events = []
        self._mitigation_events = []
        self._simplified_networks = {
            NetworkState.PRE_FAULT: None,
            NetworkState.DURING_FAULT: None,
            NetworkState.POST_FAULT: None
        }

        # Use deepcopy in order to keep references linking breakers and buses
        network = deepcopy(self)

        # Restore events and simplified networks
        self._failure_events = failure_events
        self._mitigation_events = mitigation_events
        self._simplified_networks = simplified_networks

        if simplified_networks[NetworkState.PRE_FAULT] is not None:
            network.initialize_simplified_network(simplified_networks[NetworkState.PRE_FAULT])

        return network

    def initialize_simplified_network(self, simplified_network: Tuple['SimplifiedNetwork', List[str]] = None):
        """
        Compute the simplified pre-fault network
        """
        if self._simplified_networks[NetworkState.PRE_FAULT] is not None:
            raise ValueError("Simplified PRE_FAULT network already exists")

        if simplified_network is None:
            self._simplified_networks[NetworkState.PRE_FAULT] = self.get_simplified_network()
        else:
            self._simplified_networks[NetworkState.PRE_FAULT] = simplified_network

    @property
    def pulse(self) -> float:
        """
        Return the network pulse.

        :return: The network pulse.
        """
        return 2 * pi * self.frequency

    @property
    def failure_events(self) -> List['Event']:
        """
        Get the failure events to be taken into account to derive the network states.

        return: A list of the failure events used to generate the during-fault state
        """
        return self._failure_events

    @property
    def mitigation_events(self) -> List['Event']:
        """
        Get the mitigation events to be taken into account to derive the network states.

        return: A list of the mitigation events used to generate the post-fault state
        """
        return self._mitigation_events

    @property
    def generators(self) -> List[Generator]:
        """
        Get the generators in the network.

        :return: The list of generators.
        """
        return self._generators

    @property
    def loads(self) -> List[Load]:
        """
        Get the loads in the network.

        :return: The list of loads.
        """
        return [load for bus in self.buses for load in bus.loads]

    @property
    def capacitor_banks(self) -> List[CapacitorBank]:
        """
        Get the capacitor banks in the network.

        :return: The list of capacitor banks.
        """
        return [bank for bus in self.buses for bank in bus.capacitor_banks]

    @property
    def breakers(self) -> List[ParallelBreakers]:
        """
        Get network breakers.

        :return: The list of breakers in the network.
        """
        return self._breakers

    def get_bus_coupling_map(self) -> DefaultDict[Bus, Set[Bus]]:
        """
        Get a copy of the bus coupling map
        """
        return self._bus_coupling_map

    def get_pre_fault_simplified_network(self):
        """
        Get the simplified version of the pre fault network state
        Note that the return type isn't specified because the SimplifiedNetwork type is defined later
        as it inherits the Network class
        """
        return self._simplified_networks[NetworkState.PRE_FAULT]

    def get_generator_voltage_product_amplitudes(self) -> DefaultDict:
        """
        Get the generator voltage amplitude products
        """
        return self._generator_voltage_product_amplitudes

    def get_pre_fault_admittances(self) -> AdmittanceMatrix:
        """
        Get the pre fault admittance matrix
        """
        return self._admittances[NetworkState.PRE_FAULT]

    def get_bus(self, bus_name: str) -> Bus:
        """
        Get the bus having the specified name.
        Note that this bus may have been coupled to another one in the network.

        :param bus_name: Name of the bus to identify.
        :raise ElementNotFoundException if no bus is associated to this name in the topology.
        """
        try:
            return next(bus for bus in self.buses if bus.name == bus_name or bus_name in bus.coupled_bus_names)
        except StopIteration:
            raise ElementNotFoundException(bus_name, Bus.__name__)

    def get_branch(self, first_bus_name: str, second_bus_name: str) -> Branch:
        """
        Get the branch connecting the two buses whose names are specified.
        Note that one or both buses may have been coupled to other buses.

        :param first_bus_name: Name of the first bus connected to the branch.
        :param second_bus_name: Name of the second bus connected to the branch.
        :return: The branch in between the specified buses.
        :raise ElementNotFoundException if the branch cannot be identified.
        """
        try:
            # Iterator of buses based on their names
            iterator = iter(
                bus for bus in self.buses if bus.name in {first_bus_name, second_bus_name} or
                first_bus_name in bus.coupled_bus_names or
                second_bus_name in bus.coupled_bus_names
            )
            bus = next(iterator)
            other_bus_name = (
                first_bus_name
                if bus.name == second_bus_name or second_bus_name in bus.coupled_bus_names
                else second_bus_name
            )

            # Check branches
            return next(
                branch for branch in bus.branches if
                other_bus_name in {branch.first_bus.name, branch.second_bus.name} or
                other_bus_name in branch.first_bus.coupled_bus_names or
                other_bus_name in branch.second_bus.coupled_bus_names
            )
        except StopIteration:
            raise ElementNotFoundException(f"[{first_bus_name} - {second_bus_name}]", Branch.__name__)

    def get_parallel_breakers(self, first_bus_name: str, second_bus_name: str) -> ParallelBreakers:
        """
        Get the parallel breakers connecting the two buses whose names are specified.

        :param first_bus_name: Name of the first bus connected to the branch.
        :param second_bus_name: Name of the second bus connected to the branch.
        :return The parallel breakers between the buses.
        :raise ElementNotFoundException if the breaker cannot be identified.
        """
        try:
            # Iterator of breakers based on the bus names
            iterator = iter(
                breaker for breaker in self._breakers if
                (breaker.first_bus.name == first_bus_name and breaker.second_bus.name == second_bus_name) or
                (breaker.first_bus.name == second_bus_name and breaker.second_bus.name == first_bus_name)
            )
            return next(iterator)
        except StopIteration:
            raise ElementNotFoundException(f"[{first_bus_name} - {second_bus_name}]", Breaker.__name__)

    def get_generator(self, generator_name: str) -> Generator:
        """
        Get the generator with the specified name.

        :param generator_name: Name of the generator.
        :return: The generator with the specifief name.
        :raise: ElementNotFoundException if the generator is not found.
        """
        try:
            return next(gen for gen in self.generators if gen.name == generator_name)
        except StopIteration:
            # Generator not found
            raise ElementNotFoundException(generator_name, Generator.__name__)

    def get_coupled_buses(self, bus: Bus) -> Set[Bus]:
        """
        Get the set of buses that are coupled with a breaker to the specified bus.

        :param bus: The bus to which the other buses must be coupled.
        :return: The set of buses coupled to the specified bus, including the input bus.
        """
        coupled_buses = {bus}
        buses = {bus}
        while buses:
            current_buses = buses
            buses = set()
            for current_bus in current_buses:
                if current_bus not in self._bus_coupling_map:
                    # Bus is not coupled
                    continue
                for coupled_bus in self._bus_coupling_map[current_bus]:
                    # Bus is coupled with another one
                    if coupled_bus not in coupled_buses:
                        # Bus not already considered
                        coupled_buses.add(coupled_bus)
                        buses.add(coupled_bus)
        return coupled_buses

    def change_breaker_position(self, first_bus_name: str, second_bus_name: str, parallel_id: int, closed: bool):
        """
        Change a breaker in the network.

        :param first_bus_name: Name of the first coupled bus.
        :param second_bus_name: Name of the second coupled bus.
        :param parallel_id: Parallel ID identifying the breaker.
        :param closed: True if the breaker must be closed, False otherwise.

        :raise ElementNotFoundException if no breaker can be found between the two buses in the network.
        :raise ParallelException if no element is at the specified parallel ID on the branch.
        """
        # Get breaker
        parallel_breakers = self.get_parallel_breakers(first_bus_name, second_bus_name)
        breaker = parallel_breakers[parallel_id]

        # Open the breaker
        if breaker.closed == closed:
            # Breaker is already in the expected state.
            return
        breaker.closed = closed

        # Update coupling map
        first_bus = parallel_breakers.first_bus
        second_bus = parallel_breakers.second_bus
        if closed:
            self._bus_coupling_map[first_bus].add(second_bus)
            self._bus_coupling_map[second_bus].add(first_bus)
        else:
            self._bus_coupling_map[first_bus].remove(second_bus)
            self._bus_coupling_map[second_bus].remove(first_bus)

    @classmethod
    def create_network(
        cls, network_topology: topology_dtos.NetworkTopology, load_flow: load_flow_dtos.LoadFlowResults
    ) -> 'Network':
        """
        Create a network based on topological data and load flow data.

        :param network_topology: The topological data.
        :param load_flow: The load flow data.
        :return: A network built based on the topological and load flow data.
        :raise: DEEACExceptionList in case of errors.
        """
        # Collector for the exceptions that may occur
        exception_collector = DEEACExceptionCollector()

        # Base power in MVA for per unit conversions
        with exception_collector:
            base_power = Value.from_dto(network_topology.base_power).to_unit(Unit.MVA)
        exception_collector.raise_for_exception()

        # Create first the buses
        buses = {}
        for bus in network_topology.buses:
            with exception_collector:
                # Base voltage obtained from static data
                base_voltage = Value.from_dto(bus.base_voltage).to_unit(Unit.KV)
                try:
                    # Get load flow results for this bus
                    load_flow_bus = load_flow.buses[bus.name]
                    # Bus voltage obtained from load flow
                    voltage_magnitude = Value.from_dto(load_flow_bus.voltage).to_unit(Unit.KV)
                    if type(bus) == topology_dtos.SlackBus:
                        # Phase angle of slack bus in static data
                        phase_angle = Value.from_dto(bus.phase_angle).to_unit(Unit.RAD)
                        bus_type = BusType.SLACK
                    else:
                        # Phase angle from load flow
                        phase_angle = Value.from_dto(load_flow_bus.phase_angle).to_unit(Unit.RAD)
                        bus_type = None
                except KeyError:
                    # No load flow data for this bus
                    if type(bus) == topology_dtos.SlackBus:
                        # Slack bus must have load flow results
                        raise LoadFlowException(bus.name, Bus.__name__)
                    # Bus is probably disconnected
                    voltage_magnitude = 0
                    phase_angle = 0
                    bus_type = None

                # Generate model
                buses[bus.name] = Bus(
                    name=bus.name,
                    base_voltage=base_voltage,
                    voltage_magnitude=voltage_magnitude,
                    phase_angle=phase_angle,
                    type=bus_type
                )

        # Raise if all the buses could not be created properly
        exception_collector.raise_for_exception()

        # Create the generators
        for generator in network_topology.generators:
            with exception_collector:
                # Get bus connected to generator
                bus = get_element(generator.bus.name, buses, Bus.__name__)
                # Set type of generator
                if bus.type == BusType.SLACK:
                    generator_type = GeneratorType.SLACK
                else:
                    generator_type = GeneratorType.PV if generator.regulating else GeneratorType.PQ
                # Compute base voltage and resistance for per unit conversions
                base_voltage = bus.base_voltage
                pu_base_voltage = PUBase(value=base_voltage, unit=Unit.KV)
                pu_base_reactance = base_voltage ** 2 / base_power

                # Get load flow data
                try:
                    load_flow_generator = load_flow.generators[generator.name]
                    # Read load flow data for active (P) and reactive (Q) powers
                    active_power = Value.from_dto(load_flow_generator.active_power).to_unit(Unit.MW)
                    reactive_power = Value.from_dto(load_flow_generator.reactive_power).to_unit(Unit.MVAR)

                except KeyError:
                    # No load flow data for this generator
                    if generator_type == GeneratorType.SLACK or generator.connected:
                        # Generator must be found in the load flow results if slack or connected
                        raise LoadFlowException(generator.name, Generator.__name__)
                    # Generator probably disconnected
                    active_power = 0
                    reactive_power = 0
                if generator_type == GeneratorType.PQ:
                    target_voltage = None
                else:
                    # Slack generator, target voltage V and its angle are set
                    target_voltage = Value(
                        value=Value.from_dto(generator.target_voltage).to_unit(Unit.KV),
                        unit=Unit.KV,
                        base=pu_base_voltage
                    )

                # Convert inertia constant to system-based
                inertia_constant = Value.from_dto(generator.inertia_constant).to_unit(Unit.MWS_PER_MVA) / base_power

                # Minimum and maximum powers
                min_active_power = Value.from_dto(generator.min_active_power).to_unit(Unit.MW)
                max_active_power = Value.from_dto(generator.max_active_power).to_unit(Unit.MW)
                min_reactive_power = Value.from_dto(generator.min_reactive_power).to_unit(Unit.MVAR)
                max_reactive_power = Value.from_dto(generator.max_reactive_power).to_unit(Unit.MVAR)
                try:
                    generator_source = GeneratorSource.__getattr__(generator.source.lower())
                except AttributeError:
                    generator_source = GeneratorSource.unknown

                # Create generator model and connect it to its bus
                bus.add_generator(
                    Generator(
                        name=generator.name,
                        type=generator_type,
                        source=generator_source,
                        bus=bus,
                        pu_base_reactance=pu_base_reactance,
                        base_power=base_power,
                        direct_transient_reactance=Value.from_dto(generator.direct_transient_reactance).to_unit(Unit.OHM),
                        inertia_constant=inertia_constant,
                        min_active_power=min_active_power,
                        active_power=active_power,
                        max_active_power=max_active_power,
                        min_reactive_power=min_reactive_power,
                        reactive_power=reactive_power,
                        max_reactive_power=max_reactive_power,
                        connected=generator.connected
                    )
                )

        # Create loads
        for load in network_topology.loads:
            with exception_collector:
                # Get bus connected to generator
                bus = get_element(load.bus.name, buses, Bus.__name__)
                if load.name[:4] == "GEN_":
                    # If the load actually is a static generator
                    try:
                        load_data = load_flow.generators[load.name[4:]]
                        load_data.active_power.value = -1 * load_data.active_power.value
                        load_data.reactive_power.value = -1 * load_data.reactive_power.value
                    # If it only exists in the topological data
                    except KeyError:
                        load_data = load
                else:
                    try:
                        load_data = load_flow.loads[load.name]
                    except KeyError:
                        load_data = load

                bus.add_load(
                    Load(
                        name=load.name,
                        bus=bus,
                        base_power=base_power,
                        active_power=Value.from_dto(load_data.active_power).to_unit(Unit.MW),
                        reactive_power=Value.from_dto(load_data.reactive_power).to_unit(Unit.MVAR),
                        connected=load.connected
                    )
                )

        # Create capacitor banks
        for bank in network_topology.capacitor_banks:
            with exception_collector:
                # Get bus connected to capacitor bank
                bus = get_element(bank.bus.name, buses, Bus.__name__)
                bus.add_capacitor_bank(
                    CapacitorBank(
                        name=bank.name,
                        bus=bus,
                        base_power=base_power,
                        active_power=Value.from_dto(bank.active_power).to_unit(Unit.MW),
                        reactive_power=-1 * Value.from_dto(bank.reactive_power).to_unit(Unit.MVAR)
                    )
                )

        # Create static var compensators (modelled as capacitor banks)
        for svc in network_topology.static_var_compensators:
            with exception_collector:
                # Get reactive power from load flow results
                try:
                    load_flow_svc = load_flow.static_var_compensators[svc.name]
                    reactive_power = -1 * Value.from_dto(load_flow_svc.reactive_power).to_unit(Unit.MVAR)
                except KeyError:
                    if svc.connected:
                        # SVC must be found in the load flow results
                        raise LoadFlowException(svc.name, topology_dtos.StaticVarCompensator.__name__)
                    else:
                        # SVC is disconnected
                        reactive_power = 0
                # Get bus connected to converter
                bus = get_element(svc.bus.name, buses, Bus.__name__)
                bus.add_capacitor_bank(
                    CapacitorBank(
                        name=svc.name,
                        bus=bus,
                        base_power=base_power,
                        active_power=0,
                        reactive_power=reactive_power
                    )
                )

        # Create HVDC converters (modelled as loads)
        for hvdc_converter in network_topology.hvdc_converters:
            with exception_collector:
                # Get load flow data (powers must be negated for sign convention)
                try:
                    load_flow_hvdc_converter = load_flow.hvdc_converters[hvdc_converter.name]
                    active_power_dto = load_flow_hvdc_converter.active_power
                    active_power_dto.value = -active_power_dto.value
                    active_power = Value.from_dto(active_power_dto).to_unit(Unit.MW)
                    reactive_power_dto = load_flow_hvdc_converter.reactive_power
                    reactive_power_dto.value = -reactive_power_dto.value
                    reactive_power = Value.from_dto(reactive_power_dto).to_unit(Unit.MVAR)
                except KeyError:
                    if hvdc_converter.connected:
                        # HVDC converter must be found in the load flow results
                        raise LoadFlowException(hvdc_converter.name, topology_dtos.HVDCConverter.__name__)
                    else:
                        # HVDC converter is disconnected
                        active_power = 0
                        reactive_power = 0
                # Get bus connected to converter
                bus = get_element(hvdc_converter.bus.name, buses, Bus.__name__)
                bus.add_load(
                    Load(
                        name=hvdc_converter.name,
                        bus=bus,
                        base_power=base_power,
                        active_power=active_power,
                        reactive_power=reactive_power,
                        connected=hvdc_converter.connected
                    )
                )

        # Create the branches and breakers
        # N.B: Breakers are in a branch in practice, as they connect two buses, but in the models they are considered
        # differently as lines and transformers
        breakers = []
        for branch_dto in network_topology.branches:
            # Get connected buses
            first_bus = get_element(branch_dto.sending_bus.name, buses, Bus.__name__)
            second_bus = get_element(branch_dto.receiving_bus.name, buses, Bus.__name__)

            # Get expected branch type
            branch_type = type(next(iter(branch_dto.parallel_elements.values())))
            if branch_type == topology_dtos.Breaker:
                # Branch is a set of parallel breakers
                branch = ParallelBreakers(first_bus=first_bus, second_bus=second_bus)
                breakers.append(branch)
            else:
                # Branch is a set of transformers and/or lines
                branch = Branch(first_bus=first_bus, second_bus=second_bus)
                first_bus.add_branch(branch)
                second_bus.add_branch(branch)

            # Get parallel elements
            for (parallel_id, element) in branch_dto.parallel_elements.items():
                element_type = type(element)
                if element_type == topology_dtos.Breaker:
                    # Breaker
                    branch[parallel_id] = Breaker(closed=element.closed)
                elif element_type == topology_dtos.Line:
                    # Line
                    # Compute base for per unit conversions
                    sending_bus_base_voltage = first_bus.base_voltage
                    receiving_bus_base_voltage = second_bus.base_voltage
                    base_impedance = sending_bus_base_voltage * receiving_bus_base_voltage / base_power
                    # Create line model
                    branch[parallel_id] = Line(
                        base_impedance=base_impedance,
                        resistance=Value.from_dto(element.resistance).to_unit(Unit.OHM),
                        reactance=Value.from_dto(element.reactance).to_unit(Unit.OHM),
                        shunt_conductance=Value.from_dto(element.shunt_conductance).to_unit(Unit.S),
                        shunt_susceptance=Value.from_dto(element.shunt_susceptance).to_unit(Unit.S),
                        closed_at_first_bus=element.closed_at_sending_bus,
                        closed_at_second_bus=element.closed_at_receiving_bus
                    )
                # Transformer
                elif element_type in (topology_dtos.Transformer1, topology_dtos.Transformer8):
                    # Ignore disconnected elements
                    if element.closed_at_sending_bus is False or element.closed_at_receiving_bus is False:
                        continue

                    if element_type == topology_dtos.Transformer8:
                        try:
                            tap_data = load_flow.transformer_tap_data[
                                f"{branch.first_bus.name}_{branch.second_bus.name}_{parallel_id}"]
                        except KeyError:
                            try:
                                tap_data = load_flow.transformer_tap_data[
                                    f"{branch.second_bus.name}_{branch.first_bus.name}_{parallel_id}"]
                            except KeyError:
                                raise LoadFlowException(f"{branch.first_bus.name}_{branch.second_bus.name}",
                                                        "transformer_tap_data")
                        transformer_type = 8
                        tap_index = tap_data.tap_numbers.index(element.initial_tap_number)
                        sending_node_voltage = tap_data.sending_node_voltages[tap_index]
                        receiving_node_voltage = tap_data.receiving_node_voltages[tap_index]
                        ratio = (branch.first_bus.base_voltage / sending_node_voltage) \
                                * (receiving_node_voltage / branch.second_bus.base_voltage)
                        phase_shift_angle = Value(value=tap_data.phase_angles[tap_index], unit=Unit.DEG)
                    else:
                        transformer_type = 1
                        ratio = element.ratio
                        phase_shift_angle = None

                    first_node_data = load_flow.transformer_nodes_data[branch.first_bus.name]
                    second_node_data = load_flow.transformer_nodes_data[branch.second_bus.name]
                    second_bus_indices = [i for i, node in enumerate(first_node_data.nodes)
                                          if node == branch.second_bus.name and first_node_data.parallel_ids[
                                              i] == parallel_id]

                    first_bus_indices = [i for i, node in enumerate(second_node_data.nodes)
                                         if node == branch.first_bus.name and second_node_data.parallel_ids[
                                             i] == parallel_id]
                    second_bus_index = second_bus_indices[0]
                    first_bus_index = first_bus_indices[0]

                    resistance = first_node_data.resistances[second_bus_index]
                    if resistance != second_node_data.resistances[first_bus_index]:
                        raise ValueError(f"Resistance error")
                    reactance = first_node_data.reactances[second_bus_index]
                    if reactance != second_node_data.reactances[first_bus_index]:
                        raise ValueError(f"Reactance error")
                    shunt_conductance = first_node_data.shunt_conductances[second_bus_index]
                    if shunt_conductance != second_node_data.shunt_conductances[first_bus_index]:
                        raise ValueError(f"Shunt conductance error")
                    shunt_susceptance = first_node_data.resistances[second_bus_index]
                    if first_node_data.shunt_susceptances[second_bus_index] != second_node_data.shunt_susceptances[first_bus_index]:
                        raise ValueError(f"Shunt susceptance error")

                    base_impedance = PUBase(value=element.base_impedance.value, unit=Unit.OHM).value
                    resistance = float(resistance) * base_impedance
                    reactance = float(reactance) * base_impedance
                    shunt_conductance = float(shunt_conductance) / base_impedance
                    shunt_susceptance = float(shunt_susceptance) / base_impedance

                    # Create transformer model
                    branch[parallel_id] = Transformer(
                        base_impedance=base_impedance,
                        resistance=resistance,
                        reactance=reactance,
                        shunt_conductance=shunt_conductance,
                        shunt_susceptance=shunt_susceptance,
                        ratio=ratio,
                        phase_shift_angle=phase_shift_angle,
                        sending_node=element.sending_node,
                        receiving_node=element.receiving_node,
                        closed_at_first_bus=element.closed_at_sending_bus,
                        closed_at_second_bus=element.closed_at_receiving_bus,
                        transformer_type=transformer_type
                    )
                else:
                    # Unknown type of element
                    raise BranchContentException(first_bus.name, second_bus.name)

        # Raise if any exceptions
        exception_collector.raise_for_exception()

        # Create and return the network
        return cls(
            buses=list(buses.values()),
            breakers=breakers,
            base_power=Value.from_dto(network_topology.base_power)
        )

    def provide_events(self, failure_events: List['Event'], mitigation_events: List['Event']) -> bool:
        """
        Provide the failure and mitigation events to allow the computation of the simplified networks in specific
        states. Providing new events will recompute the network states, ignoring events that may already have been
        provided previously.

        :param failure_events: List of failure events to derive the during-fault state.
        :param mitigation_events: List of mitigation events use to derive the post-fault state.
        :return: a bool signaling whether the fault happened on a disconnected line, thus ending the execution
        """
        # Remove during and post-fault simplified networks
        self._simplified_networks[NetworkState.DURING_FAULT] = None
        self._simplified_networks[NetworkState.POST_FAULT] = None

        # Copy events so that any modification of an event will not be replicated in this network
        self._failure_events = failure_events
        self._mitigation_events = mitigation_events

        # The pre-fault network is common to every parallel seq file, it is computed in the main

        # Derive during fault network
        during_fault_network = self.duplicate()
        relevant_fault_event = False
        for fault in self._failure_events:
            relevant_fault_event += fault.apply_to_network(during_fault_network)
        # If all the failure events happen on disconnected element, then cancel the entire execution
        # However, if any of the failures happens on a live element, continue the computation
        if not relevant_fault_event:
            raise IOError("Failure events happening on disconnected elements, cancelling execution")

        self._simplified_networks[NetworkState.DURING_FAULT] = during_fault_network.get_simplified_network()

        # Derive post fault network
        post_fault_network = during_fault_network
        for mitigation in self._mitigation_events:
            try:
                mitigation.apply_to_network(post_fault_network)
            # If a mitigation event happens on an open line is inconsequential
            except IOError:
                pass
            except ParallelException:
                print("Warning: opening a circuit breaker that is already open is impossible")
                pass

        self._simplified_networks[NetworkState.POST_FAULT] = post_fault_network.get_simplified_network()

    def get_disconnected_buses(self, state: NetworkState):
        """
        Get the list of the names of the buses that were discarded in a specified network state.
        A bus is discarded if it is not connected to the main network component during the graph analysis.

        :param state: The network state to consider.
        :return: The list of the names of the buses that were discarded.
        """
        if self._simplified_networks[state] is None:
            # Events were not provided
            raise NetworkStateException()
        return self._simplified_networks[state][1]

    def get_state(self, state: NetworkState) -> 'SimplifiedNetwork':
        """
        Return a simplified version of this network in the specified state.

        :param state: The state for which the simplified network is requested.
        :return: The simplified network in the expected state.
        :raise NetworkStateException if a state requires events that were not provided previously.
        """
        if self._simplified_networks[state] is None:
            # Events were not provided
            raise NetworkStateException()
        return self._simplified_networks[state][0]

    def get_simplified_network(self) -> Tuple['SimplifiedNetwork', List[str]]:
        """
        Return a simplified version of this network with the following characteristics:
            1. Buses connected by a breaker are merged
            2. Contains only connected generators and loads
            3. Contains only closed lines and transformers
            4. Contains only the buses and branches belonging to a connected graph
            5. A fictive bus is added for each generator to represent their internal voltage
        This function also returns the list of the names of the buses that were discarded during the graph analysis to
        create this simplified version of the network.

        :param state: The state for which the simplified network is requested.
        :return: The simplified network in the expected state and the list of the names of the buses that were
                 discarded.
        :raise NetworkEventException if a state requires events that were not provided previously.
        """
        # Copy network
        network = self.duplicate()

        # Couple buses
        coupled_buses = dict()
        bus_map = defaultdict(list)
        for breaker in network.breakers:
            if not breaker.closed:
                # Breaker is opened
                continue
            first_bus = breaker.first_bus
            second_bus = breaker.second_bus
            # Check if buses were already coupled previously
            if first_bus in coupled_buses:
                first_bus = coupled_buses[first_bus]
            if second_bus in coupled_buses:
                second_bus = coupled_buses[second_bus]
            # Merge the buses if different
            if first_bus != second_bus:
                first_bus.couple_to_bus(second_bus)
                def update_references(bus_map, bus_to_update, new_reference_bus):
                    # Previous references to second bus are updated
                    for bus in bus_map[bus_to_update]:
                        coupled_buses[bus] = new_reference_bus
                        if bus in bus_map:
                            update_references(bus_map, bus, new_reference_bus)
                update_references(bus_map, second_bus, first_bus)
                coupled_buses[second_bus] = first_bus
                bus_map[first_bus].append(second_bus)
        # Remove buses that were coupled to another one
        network.buses = [bus for bus in network.buses if bus not in coupled_buses]
        # No breaker in the simplified network as buses were merged
        network.breakers.clear()

        # Get graph corresponding to network where nodes are buses and vertices are branches
        network_graph = nx.Graph()
        edges = []
        for bus in network.buses:
            for branch in bus.branches:
                if branch.closed:
                    edges.append((branch.first_bus.name, branch.second_bus.name))
        network_graph.add_edges_from(edges)

        # Get the largest set of connected buses
        connected_buses = max(nx.connected_components(network_graph), key=len)
        disconnected_buses = []
        buses = []
        for bus in network.buses:
            if bus.name in connected_buses:
                buses.append(bus)
            else:
                disconnected_buses += bus.coupled_bus_names
        network.buses = buses

        # Raise an error if more than one slack bus is connected
        slack_bus_names = [bus.name for bus in network.buses if bus.type == BusType.SLACK]
        if len(slack_bus_names) > 1:
            raise MultipleSlackBusException(slack_bus_names)
        if not slack_bus_names:
            raise NoSlackBusException()

        analyzed_branches = set()
        for bus in network.buses:
            branches = list()
            for branch in bus.branches:
                if branch in analyzed_branches:
                    # Branch already considered
                    branches.append(branch)
                    continue
                # Remove opened branches and branches whose at least one of the extremities is not in the set of
                # connected buses
                if (
                    branch.closed and
                    branch.first_bus.name in connected_buses and
                    branch.second_bus.name in connected_buses
                ):
                    elements = dict()
                    for parallel_id in branch.parallel_elements:
                        # Keep only closed elements
                        if branch.parallel_elements[parallel_id].closed:
                            elements[parallel_id] = branch.parallel_elements[parallel_id]
                    branch.parallel_elements = elements
                    analyzed_branches.add(branch)
                    branches.append(branch)
            bus.branches = branches

            # Remove generators and loads that are not connected
            bus.generators = [generator for generator in bus.generators if generator.connected]
            bus.loads = [load for load in bus.loads if load.connected]

        # Add fictive buses for the internal voltage of each generator
        fictive_buses = list()
        for bus in network.buses:
            for generator in bus.generators:
                if not generator.connected or generator.bus.type == BusType.GEN_INT_VOLT:
                    # Consider only connected generators that are not already connected to a fictive bus
                    continue
                # Create fictive bus for the generator
                base_voltage = bus.base_voltage
                internal_voltage = generator.internal_voltage
                voltage_magnitude = abs(internal_voltage) * base_voltage
                phase_angle = phase(internal_voltage)
                fictive_generator_bus = Bus(
                    name=f"INTERNAL_VOLTAGE_{generator.name}",
                    base_voltage=base_voltage,
                    voltage_magnitude=voltage_magnitude,
                    phase_angle=phase_angle,
                    type=BusType.GEN_INT_VOLT
                )
                fictive_generator_bus.add_generator(generator)
                generator.bus = fictive_generator_bus
                fictive_buses.append(fictive_generator_bus)
                # Create a branch between fictive and real buses with a single line whose reactance if the generator
                # direct transient reactance
                base_impedance = base_voltage ** 2 / network.base_power.to_unit(Unit.MVA)
                branch = Branch(fictive_generator_bus, bus)
                fictive_generator_line = Line(
                    base_impedance=base_impedance,
                    resistance=0,
                    reactance=generator.direct_transient_reactance_pu * base_impedance,
                    shunt_conductance=0,
                    shunt_susceptance=0
                )
                branch["1"] = fictive_generator_line
                fictive_generator_bus.add_branch(branch)
                bus.add_branch(branch)

            if bus.type != BusType.GEN_INT_VOLT:
                # All the generators should be connected to a fictive bus
                bus.generators.clear()
        network.buses += fictive_buses

        return SimplifiedNetwork(buses=network.buses, base_power=network.base_power), disconnected_buses

    def _compute_generator_voltage_amplitude_product(self):
        """
        Compute the product of internal voltage amplitudes for each pair of generators in the network.
        """
        generator_voltage_product_amplitudes = dict()
        name_voltage_pairs = [(generator.name, generator.internal_voltage) for generator in self.generators]
        for n, (name1, voltage1) in enumerate(name_voltage_pairs):
            for (name2, voltage2) in name_voltage_pairs[n:]:
                # Compute product
                product = abs(voltage1 * voltage2)
                generator_voltage_product_amplitudes[(name1, name2)] = product
                generator_voltage_product_amplitudes[(name2, name1)] = product
        return generator_voltage_product_amplitudes

    @lru_cache(maxsize=None)
    def get_generator_voltage_amplitude_product(self, generator1_name: str, generator2_name: str) -> float:
        """
        Compute the product of two generator internal voltage amplitudes.

        :param generator1_name: Name of the first generator to consider.
        :param generator2_name: Name of the second generator to consider.
        :return: The product of the generator internal voltage amplitudes.
        :raise: ElementNotFoundException if one of the generators cannot be found.
        """
        try:
            return self._generator_voltage_product_amplitudes[(generator1_name, generator2_name)]
        except KeyError:
            # Generator does not exist
            raise ElementNotFoundException(f"{generator1_name} or {generator2_name}", Generator.__name__)

    def get_admittance(self, bus1_name: str, bus2_name: str, state: NetworkState) -> Tuple[float, float]:
        """
        Compute the admittance amplitude and angle from the reduced admittance matrix for a pair of buses in the
        specified network state.

        :param bus1_name: Name of the first bus to consider.
        :param bus2_name: Name of the second bus to consider.
        :param state: Network state to consider.
        :return: A tuple corresponding to the amplitude and angle of the admittance.
        """
        # Check if admittance already computed
        admittances = self._admittances[state]
        try:
            return admittances[(bus1_name, bus2_name)]
        except KeyError:
            # Compute admittance amplitude and angle
            network = self.get_state(state)
            admittance_matrix = network.admittance_matrix.reduction
            admittance = admittance_matrix[bus1_name, bus2_name]
            amplitude = abs(admittance)
            angle = phase(admittance)
            admittances[(bus1_name, bus2_name)] = (amplitude, angle)
            return amplitude, angle

    def _build_bus_coupling_map(self) -> DefaultDict[Bus, Set[Bus]]:
        """
        Create a map describing how buses are coupled.
        Each bus of the map is associaed the list of the other buses to which it is coupled.

        :return: The cooupling map.
        """
        coupling_map = defaultdict(set)
        for breaker in self.breakers:
            if not breaker.closed:
                # Breaker is opened
                continue
            first_bus = breaker.first_bus
            second_bus = breaker.second_bus
            coupling_map[first_bus].add(second_bus)
            coupling_map[second_bus].add(first_bus)
        return coupling_map

    @staticmethod
    def _get_buses_in_perimeter(bus: Bus, diameter: int) -> Set[Bus]:
        """
        Get a set of neighboring buses that are located in a delimited perimeter of a given bus.

        :param bus: Bus at the center of the perimeter.
        :return: Set of neighbors that are located in the perimeter of the bus. The bus is also included in the set.
        """
        buses = {bus}
        neighbor_buses = {bus}
        current_diameter = 0
        while current_diameter < diameter and neighbor_buses:
            new_neighbor_buses = set()
            for neighbor_bus in neighbor_buses:
                for branch in neighbor_bus.branches:
                    if not branch.closed:
                        continue
                    bus = branch.first_bus if neighbor_bus != branch.first_bus else branch.second_bus
                    new_neighbor_buses.add(bus)
                    buses.add(bus)
            neighbor_buses = new_neighbor_buses
            current_diameter += 1
        return buses

    @staticmethod
    def _plot_network_graph(
        network_graph: nx.Graph, output_file: str, fictive_load_names: List[str] = None,
        discarded_bus_names: List[str] = None, discarded_branch_names: List[str] = None
    ):
        """
        Plot a network graph and output it in a file. If the path to the file exists, it is replaced.

        :param network_graph: Network graph to plot.
        :param output_file: Path to an output file.
        :param fictive_load_names: List of fictive loads (for representation purposes).
        :param discarded_bus_names: List of bus discarded buses (for representation purposes).
        :param fictive_load_names: List of discarded branches (for representation purposes).
        """
        if fictive_load_names is None:
            fictive_load_names = []
        if discarded_bus_names is None:
            discarded_bus_names = []
        if discarded_branch_names is None:
            discarded_branch_names = []

        # Color nodes and edges
        orange = "#E6743E"
        grey = "#B0B0B0"
        black = "#000000"
        blue = "#488AC7"
        node_colors = []
        for node in network_graph.nodes:
            if node in discarded_bus_names:
                node_colors.append(orange)
            elif node in fictive_load_names:
                node_colors.append(blue)
            else:
                node_colors.append(grey)
        edge_colors = []
        for node1, node2 in network_graph.edges:
            if (node1, node2) in discarded_branch_names or (node2, node1) in discarded_branch_names:
                edge_colors.append(orange)
            else:
                edge_colors.append(black)

        # Create figure
        fig, ax = plt.subplots(figsize=(25, 15))
        nx.draw_spring(network_graph, node_color=node_colors, edge_color=edge_colors, with_labels=True)

        # Create legend only (if needed)
        legend_parts = []
        if discarded_bus_names or discarded_branch_names:
            legend_parts.append((orange, "Discarded elements"))
        if fictive_load_names:
            legend_parts.append((blue, "Fictive loads"))
        if legend_parts:
            handles, labels = ax.get_legend_handles_labels()
            for color, label in legend_parts:
                patch = mpatches.Patch(color=color, label=label)
                handles.append(patch)
            plt.legend(handles=handles, loc=(0, 0))

        # Save figure
        plt.savefig(output_file)

    def draw_network(self, output_file: str, state: NetworkState, bus_name: str = None, diameter: int = 0):
        """
        Generate a graph representation of the network around a bus.
        This drawing is performed for a specific state.
        The representation is outputed in a file. If the path exists, it is replaced.

        :param output_file: Path to an output file.
        :param state: Network state to consider.
        :param bus_name: Name of the bus around which the graph must be shown. It must be used with the diameter
                         parameter to reduce the information displayed in the figure. If not specified, the whole
                         network is plotted.
        :param diameter: Diameter (i.e. number of buses) to consider around the selected bus. It must be used with the
                         bus_name parameter. It allows to reduce the information displayed in the figure in case of a
                         big network. If a value of 0 is specified, the whole network is plotted.
        """
        # Get network in specified state
        network = self.get_state(state)

        # Get bus
        if bus_name is None:
            bus = network.buses[0]
        else:
            bus = network.get_bus(bus_name)

        # Set maximum diameter if no value specified
        if diameter == 0:
            diameter = len(self.buses)

        # Get buses in the perimeter
        buses = self._get_buses_in_perimeter(bus, diameter)

        # Build graph
        fictive_load_names = set()
        network_graph = nx.Graph()
        edges = []
        for bus in buses:
            for load in bus.loads:
                # Add fictive loads as nodes in graph
                if isinstance(load, FictiveLoad):
                    fictive_load_names.add(load.name)
                    edges.append((bus.name, load.name))
            for branch in bus.branches:
                if branch.first_bus in buses and branch.second_bus in buses:
                    edges.append((branch.first_bus.name, branch.second_bus.name))
        network_graph.add_edges_from(edges)

        # Plot the graph
        self._plot_network_graph(network_graph, output_file, fictive_load_names)

    def draw_fault_network(self, output_file: str, diameter: int = 0):
        """
        Generate a graph representation of the network around the closest buses to the faults.
        This drawing is performed for the during fault state, starting from the pre-fault state, and highlighting
        elements discarded during the fault.
        The representation is outputed in a file. If the path exists, it is replaced.

        :param output_file: Path to an output file.
        :param diameter: Diameter (i.e. number of buses) to consider around the closest buses to the faults. It allows
                         to reduce the information displayed in the figure in case of a big network. If a value of 0 is
                         specified, the whole network is plotted.
        """
        # Get network in pre-fault state
        network = self.get_state(NetworkState.PRE_FAULT)

        # Get closer buses to the faults
        failure_buses = [event.get_nearest_bus(network) for event in self._failure_events]

        # Set maximum diameter if no value specified
        if diameter == 0:
            diameter = len(self.buses)

        # Get buses in pre-fault state in the perimeter
        buses = set()
        for failure_bus in failure_buses:
            buses = buses.union(self._get_buses_in_perimeter(failure_bus, diameter))

        # Get bus and branch names from pre-fault network in diameter
        bus_names = {bus.name for bus in buses}

        # Build graph
        fictive_load_names = set()
        discarded_bus_names = set()
        discarded_branch_names = set()
        network_graph = nx.Graph()
        edges = []

        # Get bus and branch names from expected state in diameter
        network = self.get_state(NetworkState.DURING_FAULT)
        state_buses = {bus for bus in network.buses if bus.name in bus_names}
        state_bus_names = {bus.name for bus in state_buses}
        state_branch_names = set()
        for bus in state_buses:
            for branch in bus.branches:
                if branch.first_bus.name in state_bus_names and branch.second_bus.name in state_bus_names:
                    state_branch_names.add((branch.first_bus.name, branch.second_bus.name))
            for load in bus.loads:
                # Add fictive loads as nodes in graph
                if isinstance(load, FictiveLoad):
                    fictive_load_names.add(load.name)
                    edges.append((bus.name, load.name))

        # Add buses in graph
        for bus in buses:
            if bus.name not in state_bus_names:
                # Bus was discarded
                discarded_bus_names.add(bus.name)
            for branch in bus.branches:
                first_bus_name = branch.first_bus.name
                second_bus_name = branch.second_bus.name
                if first_bus_name not in bus_names or second_bus_name not in bus_names:
                    # Branch not in diameter
                    continue
                edges.append((first_bus_name, second_bus_name))
                if (
                    (first_bus_name, second_bus_name) not in state_branch_names and
                    (second_bus_name, first_bus_name) not in state_branch_names
                ):
                    # Branch was discarded
                    discarded_branch_names.add((first_bus_name, second_bus_name))
        network_graph.add_edges_from(edges)

        # Plot the graph
        self._plot_network_graph(
            network_graph, output_file, fictive_load_names, discarded_bus_names, discarded_branch_names
        )


class SimplifiedNetwork(Network):
    """
    Distribution network without any breaker.
    """

    def __init__(self, buses: List[Bus], base_power: Value):
        """
        Initialize with a list of its buses.

        :param buses: List of the buses in the topology.
        :param base_power: System base power.
        """
        super().__init__(buses=buses, breakers=[], base_power=base_power)
        self._admittance_matrix = None

    @property
    def admittance_matrix(self) -> 'AdmittanceMatrix':
        """
        Compute an admittance matrix associated to this network.
        This method does not take breakers into account.

        :return: The corresponding admittance matrix, sorted so that the first indexes correspond to the buses connected
                 to at least one generator
        """
        if self._admittance_matrix is None:
            # Matrix not computed yet
            self._admittance_matrix = AdmittanceMatrix(self.buses)
        return self._admittance_matrix

    def get_parallel_breakers(self, first_bus_name: str, second_bus_name: str) -> ParallelBreakers:
        """
        Get the parallel breakers connecting the two buses whose names are specified.

        :param first_bus_name: Name of the first bus connected to the branch.
        :param second_bus_name: Name of the second bus connected to the branch.
        :raise SimplifiedNetworkBreakerException in any case.
        """
        raise SimplifiedNetworkBreakerExcepion(first_bus_name, second_bus_name)
