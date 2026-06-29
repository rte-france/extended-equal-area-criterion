"""
Module for network.

:module: network
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0f
# This file is part of the deeac project.
from __future__ import annotations

from cmath import phase, pi
from itertools import chain

import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import List, Set, Tuple, Dict, Optional, Sequence, TYPE_CHECKING
from collections import defaultdict

# TODO: All commented imports await complete refactor and
#  compacting of classes under the new program structure

from deeac.Utils.tools import deepcopy
from deeac.Models.bus import Bus
from deeac.Models.branch import Branch
from deeac.Models.breaker import Breaker, ParallelBreakers
from deeac.Models.capacitor_bank import CapacitorBank
from deeac.Models.generator import Generator
from deeac.Models.load import FictiveLoad, Load
from deeac.Models.line import Line
from deeac.Models.transformer import Transformer
from deeac.Models.matrices.admittance_matrix import AdmittanceMatrix
from deeac.Models.constants import BASE_POWER
from deeac.enums import BusType, NetworkState

if TYPE_CHECKING:
    from deeac.Models.events.fault_events import FaultEvents


def _update_references(
        bus_map: Dict[Bus, List[Bus]],
        coupled_buses: Dict[Bus, Bus],
        bus_to_update: Bus,
        new_reference_bus: Bus,
) -> None:
    """
    update references.
    
    :param bus_map: bus map.
    :param coupled_buses: coupled buses.
    :param bus_to_update: bus to update.
    :param new_reference_bus: new reference bus.
    """
    for bus in bus_map[bus_to_update]:
        coupled_buses[bus] = new_reference_bus
        if bus in bus_map:
            _update_references(bus_map, coupled_buses, bus, new_reference_bus)


def _get_buses_in_perimeter(bus: Bus, diameter: int) -> Set[Bus]:
    """
    Return buses within a perimeter around a bus.
    
    :param bus: Bus at the center of the perimeter.
    :param diameter: Diameter in number of buses.
    :return: Buses within the perimeter.
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
                candidate = branch.first_bus if neighbor_bus != branch.first_bus else branch.second_bus
                new_neighbor_buses.add(candidate)
                buses.add(candidate)
        neighbor_buses = new_neighbor_buses
        current_diameter += 1
    return buses


def _plot_network_graph(
        network_graph: nx.Graph,
        output_file: str,
        fictive_load_names: Set[str] = None,
        discarded_bus_names: Set[str] = None,
        discarded_branch_names: Set[Tuple[str, str]] = None,
) -> None:
    """
    Plot a network graph and write it to a file.
    
    :param network_graph: Network graph to plot.
    :param output_file: Path to an output file.
    :param fictive_load_names: Fictive load names.
    :param discarded_bus_names: Discarded bus names.
    :param discarded_branch_names: Discarded branch names.
    :return: Return value.
    """
    if fictive_load_names is None:
        fictive_load_names = set()
    if discarded_bus_names is None:
        discarded_bus_names = set()
    if discarded_branch_names is None:
        discarded_branch_names = set()

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

    fig, ax = plt.subplots(figsize=(25, 15))
    nx.draw_spring(network_graph, node_color=node_colors, edge_color=edge_colors, with_labels=True)

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

    plt.savefig(output_file)


class SimplifiedNetwork:
    """
    Simplifiednetwork.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar buses: buses.
    """

    def __init__(self, buses: List[Bus]):
        """
        Initialize with a list of its buses.
        
        :param buses: List of the buses in the topology.
        """
        self.buses = buses
        self._bus_map: Dict[str, Bus] = {}
        for bus in buses:
            self._bus_map[bus.name] = bus
            for coupled_name in bus.coupled_bus_names:
                self._bus_map[coupled_name] = bus
        self._admittance_matrix = None
        self._reduced_admittance_dense = None
        self._reduced_bus_index_map = None
        self._reduced_admittance_sparse = None

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

    def get_reduced_admittance_dense(self) -> Tuple[np.ndarray, Dict[str, int]]:
        """
        Return reduced admittance dense.
        
        :return: Result value.
        :rtype: Tuple[np.ndarray, Dict[str, int]]
        """
        if self._reduced_admittance_dense is None or self._reduced_bus_index_map is None:
            reduced = self.admittance_matrix.reduction
            dense = np.asarray(reduced.matrix)
            self._reduced_admittance_dense = dense
            self._reduced_bus_index_map = reduced.bus_index_map
        return self._reduced_admittance_dense, self._reduced_bus_index_map

    def get_reduced_admittance_sparse(self):
        """
        Return reduced admittance sparse.
        
        :return: Result value.
        :rtype: tuple
        """
        if self._reduced_admittance_sparse is None or self._reduced_bus_index_map is None:
            reduced = self.admittance_matrix.reduction
            matrix = reduced.matrix
            try:
                sparse = matrix.tocsc()
            except AttributeError:
                from scipy.sparse import csc_matrix
                sparse = csc_matrix(matrix)
            self._reduced_admittance_sparse = sparse
            self._reduced_bus_index_map = reduced.bus_index_map
        return self._reduced_admittance_sparse, self._reduced_bus_index_map

    def get_parallel_breakers(self, first_bus_name: str, second_bus_name: str) -> ParallelBreakers:
        """
        Get the parallel breakers connecting the two buses whose names are specified.
        
        :param first_bus_name: Name of the first bus connected to the branch.
        :param second_bus_name: Name of the second bus connected to the branch.
        """
        raise ValueError(first_bus_name, second_bus_name)

    @property
    def generators(self):
        """
        
        :return:
        """
        return [gen for bus in self.buses for gen in bus.generators]

    def get_bus(self, bus_name: str) -> Bus:
        """
        Get a bus by its name, including coupled bus aliases.
        
        :param bus_name: Name of the bus to identify.
        :return: Bus matching the name.
        """
        try:
            return self._bus_map[bus_name]
        except KeyError as exc:
            raise KeyError(bus_name, Bus.__name__) from exc


class NetworkStateView:
    """
    Networkstateview.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar network: simplified network.
    :ivar disconnected_buses: disconnected buses.
    """

    def __init__(self, network: SimplifiedNetwork, disconnected_buses: List[str]):
        """
        Initialize the object.
        
        :param network: simplified network.
        :param disconnected_buses: disconnected buses.
        :return: Return value.
        """
        self.network = network
        self.disconnected_buses = disconnected_buses


class ReducedAdmittanceArrays:
    """
    Reducedadmittancearrays.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar _amplitude: amplitude.
    :ivar _angle: angle.
    :ivar _bus_index_map: bus index map.
    """

    def __init__(self, amplitude: np.ndarray, angle: np.ndarray, bus_index_map: Dict[str, int]):
        """
        Initialize the object.
        
        :param amplitude: amplitude.
        :param angle: angle.
        :param bus_index_map: bus index map.
        :return: Return value.
        """
        self._amplitude = amplitude
        self._angle = angle
        self._bus_index_map = bus_index_map

    def get(self, bus1_name: str, bus2_name: str) -> Tuple[float, float]:
        """
        Get.
        
        :param bus1_name: bus1 name.
        :param bus2_name: bus2 name.
        :return: Return value.
        :rtype: Tuple[float, float]
        """
        try:
            i = self._bus_index_map[bus1_name]
            j = self._bus_index_map[bus2_name]
        except KeyError as exc:
            raise KeyError(str(exc), Bus.__name__) from exc
        return float(self._amplitude[i, j]), float(self._angle[i, j])


class Network:
    """
    Network.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar buses: buses.
    :ivar _breakers: breakers.
    :ivar frequency: frequency.
    :ivar _fault_events: List of pre-loaded fault events.
    """

    def __init__(self,
                 buses: Optional[List[Bus]] = None,
                 breakers: Optional[List[ParallelBreakers]] = None,
                 branches: Optional[List[Branch]] = None,
                 frequency: float = None,
                 base_power: float = BASE_POWER):
        """
        Initialize a topology with a list of its buses.

        :param buses: List of the buses in the topology.
        :param breakers: List of the breakers that couple buses in the network.
        :param branches: Optional list of branches already created.
        :param frequency: Frequency for this network (50Hz in Europe, default value). unit: Hz.
        :param base_power: Base power used for per-unit conversions.
        """
        if buses is None:
            buses = []
        if breakers is None:
            breakers = []

        if frequency is None:
            self.frequency = 50
        else:
            self.frequency = frequency
        self.base_power = base_power

        self.buses = buses
        self._breakers = breakers
        self.branches: List[Branch] = [] if branches is None else list(branches)

        # Lookup maps for parsers and fast access.
        self._bus_map: Dict[str, Bus] = {bus.name: bus for bus in self.buses}
        self._branch_map: Dict[Tuple[str, str], Branch] = {}
        self._load_map: Dict[str, Load] = {}
        self._generator_map: Dict[str, Generator] = {}
        self._capacitor_bank_map: Dict[str, CapacitorBank] = {}
        self._svc_map: Dict[str, CapacitorBank] = {}
        self._hvdc_map: Dict[str, Load] = {}

        # Different simplified versions of the network, with the buses that were discarded in graph analysis

        self._fault_events: List[FaultEvents] = []

        # Get generators to avoid expensive operations
        self._generators: List[Generator] = [generator for bus in buses for generator in bus.generators]
        for generator in self._generators:
            self._generator_map[generator.name] = generator
        for bus in self.buses:
            for load in bus.loads:
                self._load_map[load.name] = load
            for bank in bus.capacitor_banks:
                self._capacitor_bank_map[bank.name] = bank
        for branch in self.branches:
            key = (branch.first_bus.name, branch.second_bus.name)
            self._branch_map[key] = branch
            branch_type = type(next(iter(branch.parallel_elements.values())))
            if branch_type == Breaker:
                if branch not in self._breakers:
                    self._breakers.append(branch)
            else:
                branch.first_bus.add_branch(branch)
                branch.second_bus.add_branch(branch)

    @property
    def fault_events(self) -> List[FaultEvents]:
        """
        Return the list of pre-loaded fault events.

        :return: Fault events.
        """
        return list(self._fault_events)

    def set_fault_events(self, fault_events: Sequence[FaultEvents]) -> None:
        """
        Replace the stored fault event list.

        :param fault_events: Fault event list to store.
        """
        self._fault_events = list(fault_events)

    def add_fault_events(self, fault_events: FaultEvents) -> None:
        """
        Add a fault event entry to the list.

        :param fault_events: Fault events to add.
        """
        self._fault_events.append(fault_events)

    def clear_fault_events(self) -> None:
        """
        Clear stored fault events.

        :return: Return value.
        """
        self._fault_events = []

    def add_bus(self, bus: Bus) -> None:
        """
        Add a bus to the network.

        :param bus: Bus to add.
        """
        if bus.name in self._bus_map:
            raise ValueError(f"Bus {bus.name} already exists")
        self.buses.append(bus)
        self._bus_map[bus.name] = bus

    def get_bus_exact(self, bus_name: str) -> Bus:
        """
        Get a bus by its exact name.

        :param bus_name: Bus name.
        :return: Bus.
        """
        return self._bus_map[bus_name]

    def add_branch(
            self,
            sending_bus: Bus,
            receiving_bus: Bus,
            element: Line | Transformer | Breaker,
            parallel_id: str = "",
    ) -> None:
        """
        Add a branch element to the network.

        :param sending_bus: Sending bus.
        :param receiving_bus: Receiving bus.
        :param element: Line/Transformer/Breaker element.
        :param parallel_id: Parallel ID.
        """
        key = (sending_bus.name, receiving_bus.name)
        branch = self._branch_map.get(key)
        if branch is None:
            branch = Branch(first_bus=sending_bus, second_bus=receiving_bus)
            self.branches.append(branch)
            self._branch_map[key] = branch
        if parallel_id == "":
            parallel_id = f"{len(branch.parallel_elements)}"
        elif parallel_id in branch.parallel_elements:
            print(f"Duplicated parallel element {sending_bus.name}-{receiving_bus.name}-{parallel_id}")
        branch.parallel_elements[parallel_id] = element

        if isinstance(element, Breaker):
            if branch not in self._breakers:
                self._breakers.append(branch)
        else:
            sending_bus.add_branch(branch)
            receiving_bus.add_branch(branch)

    def check_load_name(self, name: str) -> None:
        """
        Check if a load name already exists.

        :param name: Load name.
        """
        if name in self._load_map:
            raise ValueError(f"Load '{name}' already exists")

    def add_load(self, load: Load) -> None:
        """
        Add a load to the network.

        :param load: Load to add.
        """
        self.check_load_name(load.name)
        self._load_map[load.name] = load
        load.bus.add_load(load)

    def add_generator(self, generator: Generator) -> None:
        """
        Add a generator to the network.

        :param generator: Generator to add.
        """
        if generator.name in self._generator_map:
            raise ValueError(f"Generator '{generator.name}' already exists")
        self._generator_map[generator.name] = generator
        self._generators.append(generator)
        generator.bus.add_generator(generator)

    def add_capacitor_bank(self, capacitor_bank: CapacitorBank) -> None:
        """
        Add a capacitor bank to the network.

        :param capacitor_bank: Capacitor bank to add.
        """
        if capacitor_bank.name in self._capacitor_bank_map:
            raise ValueError(f"Capacitor bank '{capacitor_bank.name}' already exists")
        self._capacitor_bank_map[capacitor_bank.name] = capacitor_bank
        capacitor_bank.bus.add_capacitor_bank(capacitor_bank)

    def add_static_var_compensator(self, svc: CapacitorBank) -> None:
        """
        Add a static var compensator to the network.

        :param svc: SVC to add.
        """
        if svc.name in self._svc_map:
            raise ValueError(f"SVC '{svc.name}' already exists")
        self._svc_map[svc.name] = svc
        svc.bus.add_capacitor_bank(svc)

    def add_hvdc_converter(self, converter: Load) -> None:
        """
        Add an HVDC converter to the network.

        :param converter: HVDC converter to add.
        """
        if converter.name in self._hvdc_map:
            raise ValueError(f"HVDC converter '{converter.name}' already exists")
        self._hvdc_map[converter.name] = converter
        converter.bus.add_load(converter)

    @property
    def bus_map(self) -> Dict[str, Bus]:
        """
        Map of buses by name.

        :return: Bus map.
        """
        return self._bus_map

    @property
    def generator_map(self) -> Dict[str, Generator]:
        """
        Map of generators by name.

        :return: Generator map.
        """
        return self._generator_map

    @property
    def load_map(self) -> Dict[str, Load]:
        """
        Map of loads by name.

        :return: Load map.
        """
        return self._load_map

    @property
    def hvdc_map(self) -> Dict[str, Load]:
        """
        Map of HVDC converters by name.

        :return: HVDC map.
        """
        return self._hvdc_map

    @property
    def svc_map(self) -> Dict[str, CapacitorBank]:
        """
        Map of SVCs by name.

        :return: SVC map.
        """
        return self._svc_map

    def duplicate(self) -> 'Network':
        """
        Duplicate itself while sharing the pre-loaded fault events.
        
        :return: A duplicated version of this network.
        """
        # Use deepcopy in order to keep references linking breakers and buses
        network = deepcopy(self)
        network._fault_events = self._fault_events
        return network

    def initialize_simplified_network(
            self,
            computed: "NetworkComputed",
            simplified_network: NetworkStateView = None,
    ) -> None:
        """
        Initialize simplified network.
        
        :param computed: Computed network cache.
        :param simplified_network: simplified network.
        """
        if computed.simplified_pre is not None:
            raise ValueError("Simplified PRE_FAULT network already exists")

        if simplified_network is None:
            computed.simplified_pre = self.get_simplified_network()
        else:
            computed.simplified_pre = simplified_network

    @property
    def pulse(self) -> float:
        """
        Return the network pulse.
        
        :return: The network pulse.
        """
        return 2 * pi * self.frequency

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
    def non_fictive_loads(self) -> List[Load]:
        """
        Get the actual loads in the network, meaning
        that the fictive loads that are added to model a fault are
        not returned.
        
        :return: The list of non fictive loads.
        """
        return [load for bus in self.buses for load in bus.loads
                if not isinstance(load, FictiveLoad)]

    @property
    def capacitor_banks(self) -> List[CapacitorBank]:
        """
        Get the capacitor banks in the network.
        
        :return: The list of capacitor banks.
        """
        return [bank for bus in self.buses for bank in bus.capacitor_banks]

    def clear_breakers(self):

        self._breakers.clear()

    @property
    def breakers(self) -> List[ParallelBreakers]:
        """
        Get network breakers.
        
        :return: The list of breakers in the network.
        """
        return self._breakers

    def get_generator_voltage_product_matrix(self, computed: "NetworkComputed") -> np.ndarray:
        """
        Return generator voltage product matrix.
        
        :param computed: Computed network cache.
        :return: Result value.
        """
        _, voltage_matrix = computed.ensure_generator_voltage_matrix(self)
        return voltage_matrix

    def get_generator_index_map(self, computed: "NetworkComputed") -> Dict[str, int]:
        """
        Return generator index map.
        
        :param computed: Computed network cache.
        :return: Result value.
        :rtype: Dict[str, int]
        """
        index_map, _ = computed.ensure_generator_voltage_matrix(self)
        return index_map

    def get_bus(self, bus_name: str) -> Bus:
        """
        Get the bus having the specified name.
        Note that this bus may have been coupled to another one in the network.
        
        :param bus_name: Name of the bus to identify.
        """
        try:
            return next(bus for bus in self.buses if bus.name == bus_name or bus_name in bus.coupled_bus_names)
        except StopIteration:
            raise KeyError(bus_name, Bus.__name__)

    def get_branch(self, first_bus_name: str, second_bus_name: str) -> Branch:
        """
        Get the branch connecting the two buses whose names are specified.
        Note that one or both buses may have been coupled to other buses.
        
        :param first_bus_name: Name of the first bus connected to the branch.
        :param second_bus_name: Name of the second bus connected to the branch.
        :return: The branch in between the specified buses.
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
            raise KeyError(f"[{first_bus_name} - {second_bus_name}]", Branch.__name__)

    def get_parallel_breakers(self, first_bus_name: str, second_bus_name: str) -> ParallelBreakers:
        """
        Get the parallel breakers connecting the two buses whose names are specified.
        
        :param first_bus_name: Name of the first bus connected to the branch.
        :param second_bus_name: Name of the second bus connected to the branch.
        :return The parallel breakers between the buses.
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
            raise KeyError(f"[{first_bus_name} - {second_bus_name}]", Breaker.__name__)

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
            raise KeyError(generator_name, Generator.__name__)

    def change_breaker_position(self, first_bus_name: str, second_bus_name: str, parallel_id: str, closed: bool):
        """
        Change a breaker in the network.
        
        :param first_bus_name: Name of the first coupled bus.
        :param second_bus_name: Name of the second coupled bus.
        :param parallel_id: Parallel ID identifying the breaker.
        :param closed: True if the breaker must be closed, False otherwise.
        
        """
        # Get breaker
        parallel_breakers = self.get_parallel_breakers(first_bus_name, second_bus_name)
        breaker = parallel_breakers[parallel_id]

        # Open the breaker
        if breaker.closed == closed:
            # Breaker is already in the expected state.
            return
        breaker.closed = closed

    @staticmethod
    def get_disconnected_buses(computed: "NetworkComputed", state: NetworkState):
        """
        Get the list of the names of the buses that were discarded in a specified network state.
        A bus is discarded if it is not connected to the main network component during the graph analysis.
        
        :param computed: Computed network cache.
        :param state: The network state to consider.
        :return: The list of the names of the buses that were discarded.
        """
        simplified = computed.get_simplified_for_state(state)
        if simplified is None:
            raise ValueError()
        return simplified.disconnected_buses

    @staticmethod
    def get_state(computed: "NetworkComputed", state: NetworkState) -> NetworkStateView:
        """
        Return a simplified version of this network in the specified state.
        
        :param computed: Computed network cache.
        :param state: The state for which the simplified network is requested.
        :return: The simplified network in the expected state.
        """
        simplified = computed.get_simplified_for_state(state)
        if simplified is None:
            raise ValueError()
        return simplified

    def get_simplified_network(self) -> NetworkStateView:
        """
        Return a simplified version of this network with the following characteristics:
        1. Buses connected by a breaker are merged
        2. Contains only connected generators and loads
        3. Contains only closed lines and transformers
        4. Contains only the buses and branches belonging to a connected graph
        5. A fictive bus is added for each generator to represent their internal voltage
        This function also returns the list of the names of the buses that were discarded during the graph analysis to
        create this simplified version of the network.
        
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

                _update_references(bus_map, coupled_buses, second_bus, first_bus)
                coupled_buses[second_bus] = first_bus
                bus_map[first_bus].append(second_bus)

        # Remove buses that were coupled to another one
        network_buses_short = [bus for bus in network.buses if bus not in coupled_buses]
        # No breaker in the simplified network as buses were merged
        network.breakers.clear()

        # Get graph corresponding to network where nodes are buses and vertices are branches
        edges = [
            (branch.first_bus.name, branch.second_bus.name)
            for bus in network_buses_short
            for branch in bus.branches
            if branch.closed
        ]
        network_graph = nx.Graph()
        network_graph.add_edges_from(edges)

        # Get the largest set of connected buses
        connected_buses = max(nx.connected_components(network_graph), key=len)
        connected_buses_set = set(connected_buses)
        disconnected_buses = list(chain.from_iterable(
            bus.coupled_bus_names for bus in network_buses_short if bus.name not in connected_buses_set
        ))
        network_buses_short = [bus for bus in network_buses_short if bus.name in connected_buses_set]

        # Raise an error if more than one slack bus is connected
        slack_bus_names = [bus.name for bus in network_buses_short if bus.type == BusType.SLACK]
        if len(slack_bus_names) > 1:
            raise ValueError(slack_bus_names)
        if not slack_bus_names:
            raise ValueError()

        analyzed_branches = set()
        for bus in network_buses_short:
            branches = set()
            for branch in bus.branches:
                if branch in analyzed_branches:
                    # Branch already considered
                    branches.add(branch)
                    continue

                # Remove opened branches and branches whose at least one of the extremities is not in the set of
                # connected buses
                if (branch.closed and
                        branch.first_bus.name in connected_buses and
                        branch.second_bus.name in connected_buses):
                    branch.parallel_elements = {
                        k: v for k, v in branch.parallel_elements.items() if v.closed
                    }
                    analyzed_branches.add(branch)
                    branches.add(branch)
            bus.branches = branches

            # Remove generators and loads that are not connected
            bus.generators = set(generator for generator in bus.generators if generator.connected)
            bus.loads = set(load for load in bus.loads if load.connected)

        # Add fictive buses for the internal voltage of each generator
        fictive_buses = list()
        for bus in network_buses_short:
            base_voltage = bus.base_voltage
            for generator in bus.generators:
                if not generator.connected or generator.bus.type == BusType.GEN_INT_VOLT:
                    # Consider only connected generators that are not already connected to a fictive bus
                    continue

                # Create fictive bus for the generator
                internal_voltage = generator.internal_voltage
                voltage_magnitude = abs(internal_voltage) * base_voltage
                phase_angle = phase(internal_voltage)
                fictive_generator_bus = Bus(
                    name=f"INTERNAL_VOLTAGE_{generator.name}",
                    base_voltage=base_voltage,
                    voltage_magnitude=voltage_magnitude,
                    phase_angle=phase_angle,
                    tpe=BusType.GEN_INT_VOLT
                )
                fictive_generator_bus.add_generator(generator)
                generator.bus = fictive_generator_bus
                fictive_buses.append(fictive_generator_bus)

                # Create a branch between fictive and real buses with a single line whose reactance if the generator
                # direct transient reactance
                base_impedance = base_voltage ** 2 / BASE_POWER
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
        network_buses_short += fictive_buses

        return NetworkStateView(SimplifiedNetwork(buses=network_buses_short), disconnected_buses)

    def get_generator_voltage_amplitude_product(
            self,
            computed: "NetworkComputed",
            generator1_name: str,
            generator2_name: str,
    ) -> float:
        """
        Compute the product of two generator internal voltage amplitudes.
        
        :param computed: Computed network cache.
        :param generator1_name: Name of the first generator to consider.
        :param generator2_name: Name of the second generator to consider.
        :return: The product of the generator internal voltage amplitudes.
        :raise: ElementNotFoundException if one of the generators cannot be found.
        """
        index_map, voltage_matrix = computed.ensure_generator_voltage_matrix(self)
        try:
            i = index_map[generator1_name]
            j = index_map[generator2_name]
        except KeyError:
            raise KeyError(f"{generator1_name} or {generator2_name}", Generator.__name__)
        return float(voltage_matrix[i, j])

    def get_admittance(
            self,
            computed: "NetworkComputed",
            bus1_name: str,
            bus2_name: str,
            state: NetworkState,
    ) -> Tuple[float, float]:
        """
        Compute the admittance amplitude and angle from the reduced admittance matrix for a pair of buses in the
        specified network state.
        
        :param computed: Computed network cache.
        :param bus1_name: Name of the first bus to consider.
        :param bus2_name: Name of the second bus to consider.
        :param state: Network state to consider.
        :return: A tuple corresponding to the amplitude and angle of the admittance.
        """
        reduced_arrays = computed.get_reduced_admittance_arrays_for_state(state)
        if reduced_arrays is None:
            simplified_view = self.get_state(computed, state)
            reduced_dense, bus_index_map = simplified_view.network.get_reduced_admittance_dense()
            reduced_arrays = ReducedAdmittanceArrays(
                amplitude=np.abs(reduced_dense),
                angle=np.angle(reduced_dense),
                bus_index_map=bus_index_map,
            )
            if state == NetworkState.PRE_FAULT:
                computed.reduced_pre = reduced_arrays
            elif state == NetworkState.DURING_FAULT:
                computed.reduced_during = reduced_arrays
            elif state == NetworkState.POST_FAULT:
                computed.reduced_post = reduced_arrays
        return reduced_arrays.get(bus1_name, bus2_name)


class NetworkComputed:
    """
    Networkcomputed.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar simplified_pre: simplified pre-fault network.
    :ivar simplified_during: simplified during-fault network.
    :ivar simplified_post: simplified post-fault network.
    :ivar reduced_pre: reduced admittance arrays for pre-fault.
    :ivar reduced_during: reduced admittance arrays for during-fault.
    :ivar reduced_post: reduced admittance arrays for post-fault.
    :ivar generator_index_map: generator name to index map.
    :ivar generator_voltage_product_matrix: generator voltage product matrix.
    """

    def __init__(self):
        """
        Initialize the object.
        
        :return: Return value.
        """
        self.simplified_pre: Optional[NetworkStateView] = None
        self.simplified_during: Optional[NetworkStateView] = None
        self.simplified_post: Optional[NetworkStateView] = None
        self.reduced_pre: Optional[ReducedAdmittanceArrays] = None
        self.reduced_during: Optional[ReducedAdmittanceArrays] = None
        self.reduced_post: Optional[ReducedAdmittanceArrays] = None
        self.generator_index_map: Optional[Dict[str, int]] = None
        self.generator_voltage_product_matrix: Optional[np.ndarray] = None

    def clear(self) -> None:
        """
        Clear.
        
        :return: Return value.
        :rtype: None
        """
        self.simplified_pre = None
        self.simplified_during = None
        self.simplified_post = None
        self.reduced_pre = None
        self.reduced_during = None
        self.reduced_post = None
        self.generator_index_map = None
        self.generator_voltage_product_matrix = None

    def get_simplified_for_state(
            self, state: NetworkState
    ) -> Optional[NetworkStateView]:
        """
        Return simplified for state.
        
        :param state: state.
        
        :return: Result value.
        """
        if state == NetworkState.PRE_FAULT:
            return self.simplified_pre
        if state == NetworkState.DURING_FAULT:
            return self.simplified_during
        if state == NetworkState.POST_FAULT:
            return self.simplified_post
        raise ValueError(state)

    def get_reduced_admittance_arrays_for_state(self, state: NetworkState) -> Optional[ReducedAdmittanceArrays]:
        """
        Return reduced admittance arrays for state.
        
        :param state: state.
        
        :return: Result value.
        """
        if state == NetworkState.PRE_FAULT:
            return self.reduced_pre
        if state == NetworkState.DURING_FAULT:
            return self.reduced_during
        if state == NetworkState.POST_FAULT:
            return self.reduced_post
        raise ValueError(state)

    def ensure_generator_voltage_matrix(self, network: "Network") -> Tuple[Dict[str, int], np.ndarray]:
        """
        Ensure generator voltage product matrix is computed.
        
        :param network: network.
        :return: Generator index map and voltage product matrix.
        :rtype: Tuple[Dict[str, int], np.ndarray]
        """
        if self.generator_index_map is None or self.generator_voltage_product_matrix is None:
            generators = network.generators
            names = [generator.name for generator in generators]
            self.generator_index_map = {name: i for i, name in enumerate(names)}
            voltages = np.array([abs(generator.internal_voltage) for generator in generators], dtype=float)
            self.generator_voltage_product_matrix = voltages[:, None] * voltages[None, :]
        return self.generator_index_map, self.generator_voltage_product_matrix


def draw_network(
        network: Network,
        computed: NetworkComputed,
        output_file: str,
        state: NetworkState,
        bus_name: str = None,
        diameter: int = 0,
) -> None:
    """
    Draw a graph representation of the network around a bus.
    
    :param network: Network instance.
    :param computed: Computed network cache.
    :param output_file: Path to an output file.
    :param state: Network state to consider.
    :param bus_name: Name of the bus around which the graph must be shown.
    :param diameter: Diameter (number of buses) to consider around the selected bus.
    :return: Return value.
    """
    simplified_network = network.get_state(computed, state).network

    if bus_name is None:
        bus = simplified_network.buses[0]
    else:
        bus = simplified_network.get_bus(bus_name)

    if diameter == 0:
        diameter = len(network.buses)

    buses = _get_buses_in_perimeter(bus, diameter)

    fictive_load_names = set()
    network_graph = nx.Graph()
    edges = []
    for bus in buses:
        for load in bus.loads:
            if isinstance(load, FictiveLoad):
                fictive_load_names.add(load.name)
                edges.append((bus.name, load.name))

        for branch in bus.branches:
            if branch.first_bus in buses and branch.second_bus in buses:
                edges.append((branch.first_bus.name, branch.second_bus.name))
    network_graph.add_edges_from(edges)

    _plot_network_graph(
        network_graph=network_graph,
        output_file=output_file,
        fictive_load_names=fictive_load_names,
    )


def draw_fault_network(
        network: Network,
        computed: NetworkComputed,
        output_file: str,
        failure_events: Sequence[FaultEvents],
        diameter: int = 0,
) -> None:
    """
    Draw a graph representation of the network around fault locations.
    
    :param network: Network instance.
    :param computed: Computed network cache.
    :param output_file: Path to an output file.
    :param failure_events: Failure events to locate faults.
    :param diameter: Diameter (number of buses) to consider around the closest buses to the faults.
    :return: Return value.
    """
    pre_fault_network = network.get_state(computed, NetworkState.PRE_FAULT).network
    if failure_events is None:
        raise ValueError("failure_events must be provided to draw fault locations.")
    failure_buses = [event.get_nearest_bus(pre_fault_network) for event in failure_events]

    if diameter == 0:
        diameter = len(network.buses)

    buses = set()
    for failure_bus in failure_buses:
        buses = buses.union(_get_buses_in_perimeter(failure_bus, diameter))

    bus_names = {bus.name for bus in buses}

    fictive_load_names: Set[str] = set()
    discarded_bus_names: Set[str] = set()
    discarded_branch_names: Set[Tuple[str, str]] = set()
    network_graph = nx.Graph()
    edges = []

    during_fault_network = network.get_state(computed, NetworkState.DURING_FAULT).network
    state_buses = {bus for bus in during_fault_network.buses if bus.name in bus_names}
    state_bus_names = {bus.name for bus in state_buses}
    state_branch_names = set()
    for bus in state_buses:
        for branch in bus.branches:
            if branch.first_bus.name in state_bus_names and branch.second_bus.name in state_bus_names:
                state_branch_names.add((branch.first_bus.name, branch.second_bus.name))
        for load in bus.loads:
            if isinstance(load, FictiveLoad):
                fictive_load_names.add(load.name)
                edges.append((bus.name, load.name))

    for bus in buses:
        if bus.name not in state_bus_names:
            discarded_bus_names.add(bus.name)

        for branch in bus.branches:
            first_bus_name = branch.first_bus.name
            second_bus_name = branch.second_bus.name

            if first_bus_name not in bus_names or second_bus_name not in bus_names:
                continue

            edges.append((first_bus_name, second_bus_name))
            if ((first_bus_name, second_bus_name) not in state_branch_names
                    and (second_bus_name, first_bus_name) not in state_branch_names):
                discarded_branch_names.add((first_bus_name, second_bus_name))

    network_graph.add_edges_from(edges)

    _plot_network_graph(
        network_graph=network_graph,
        output_file=output_file,
        fictive_load_names=fictive_load_names,
        discarded_bus_names=discarded_bus_names,
        discarded_branch_names=discarded_branch_names,
    )
