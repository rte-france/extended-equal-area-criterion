# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest
import numpy as np

from tests import TEST_DATA_FOLDER
from deeac.adapters.load_flow.eurostag import EurostagLoadFlowParser
from deeac.adapters.topology.eurostag import EurostagTopologyParser
from deeac.adapters.events.eurostag import EurostagEventParser
from deeac.domain.services.critical_clusters_identifier import AccelerationCriticalClustersIdentifier
from deeac.domain.models.omib import ZOOMIB, COOMIB, DOMIB
from deeac.domain.models.rotor_angle_trajectory_calculator.taylor_series import OMIBTaylorSeries, GeneratorTaylorSeries
from deeac.domain.models import Network, NetworkState, DynamicGenerator
from deeac.domain.services.eac import EAC
from deeac.domain.services.eeac import EEAC
from deeac.services.eeac_tree_loader import EEACTreeLoader
from deeac.adapters.eeac_tree.json import JSONTreeParser
from deeac.domain.models.eeac_tree import EEACTree
from deeac.services import NetworkLoader, EventLoader


@pytest.fixture
def case1_line_fault_event_loader() -> EventLoader:
    return EventLoader(
        event_parser=EurostagEventParser(
            eurostag_event_file=f"{TEST_DATA_FOLDER}/case1/case1_line.seq"
        )
    )


@pytest.fixture
def case1_bus_fault_event_loader() -> EventLoader:
    return EventLoader(
        event_parser=EurostagEventParser(
            eurostag_event_file=f"{TEST_DATA_FOLDER}/case1/case1_bus.seq"
        )
    )


@pytest.fixture
def case1_network() -> Network:
    return NetworkLoader(
        topology_parser=EurostagTopologyParser(
            ech_file=f"{TEST_DATA_FOLDER}/case1/case1.ech",
            dta_file=f"{TEST_DATA_FOLDER}/case1/case1.dta"
        ),
        load_flow_parser=EurostagLoadFlowParser(
            load_flow_results_file=f"{TEST_DATA_FOLDER}/case1/case1.lf"
        )
    ).load_network()


@pytest.fixture
def case1_filters_network() -> Network:
    return NetworkLoader(
        topology_parser=EurostagTopologyParser(
            ech_file=f"{TEST_DATA_FOLDER}/case1/case1_filters.ech",
            dta_file=f"{TEST_DATA_FOLDER}/case1/case1.dta"
        ),
        load_flow_parser=EurostagLoadFlowParser(
            load_flow_results_file=f"{TEST_DATA_FOLDER}/case1/case1.lf"
        )
    ).load_network()


@pytest.fixture
def case1_network_line_fault(case1_line_fault_event_loader) -> Network:
    network = NetworkLoader(
        topology_parser=EurostagTopologyParser(
            ech_file=f"{TEST_DATA_FOLDER}/case1/case1.ech",
            dta_file=f"{TEST_DATA_FOLDER}/case1/case1.dta"
        ),
        load_flow_parser=EurostagLoadFlowParser(
            load_flow_results_file=f"{TEST_DATA_FOLDER}/case1/case1.lf"
        )
    ).load_network()
    failure_events, mitigation_events = case1_line_fault_event_loader.load_events()
    network.initialize_simplified_network()
    network.provide_events(failure_events, mitigation_events)
    return network


@pytest.fixture
def case1_network_bus_fault(case1_bus_fault_event_loader) -> Network:
    network = NetworkLoader(
        topology_parser=EurostagTopologyParser(
            ech_file=f"{TEST_DATA_FOLDER}/case1/case1.ech",
            dta_file=f"{TEST_DATA_FOLDER}/case1/case1.dta"
        ),
        load_flow_parser=EurostagLoadFlowParser(
            load_flow_results_file=f"{TEST_DATA_FOLDER}/case1/case1.lf"
        )
    ).load_network()
    failure_events, mitigation_events = case1_bus_fault_event_loader.load_events()
    network.initialize_simplified_network()
    network.provide_events(failure_events, mitigation_events)
    return network


@pytest.fixture
def case1_line_fault_zoomib_eac(case1_network_line_fault) -> EAC:
    generators = {
        DynamicGenerator(gen) for gen in case1_network_line_fault.get_state(NetworkState.POST_FAULT).generators
    }
    identifier = AccelerationCriticalClustersIdentifier(case1_network_line_fault, generators)
    critical_cluster, non_critical_cluster = next(identifier.candidate_clusters)
    omib = ZOOMIB(case1_network_line_fault, critical_cluster, non_critical_cluster)
    return EAC(omib, np.pi / 100)


@pytest.fixture
def case1_line_fault_coomib_eac(case1_network_line_fault) -> EAC:
    generators = {
        DynamicGenerator(gen) for gen in case1_network_line_fault.get_state(NetworkState.POST_FAULT).generators
    }
    identifier = AccelerationCriticalClustersIdentifier(case1_network_line_fault, generators)
    critical_cluster, non_critical_cluster = next(identifier.candidate_clusters)
    omib = COOMIB(case1_network_line_fault, critical_cluster, non_critical_cluster)
    return EAC(omib, np.pi / 100)


@pytest.fixture
def case1_bus_fault_zoomib_eac(case1_network_bus_fault) -> EAC:
    generators = {
        DynamicGenerator(gen) for gen in case1_network_bus_fault.get_state(NetworkState.POST_FAULT).generators
    }
    identifier = AccelerationCriticalClustersIdentifier(case1_network_bus_fault, generators)
    critical_cluster, non_critical_cluster = next(identifier.candidate_clusters)
    omib = ZOOMIB(case1_network_bus_fault, critical_cluster, non_critical_cluster)
    return EAC(omib, np.pi / 100)


@pytest.fixture
def case1_line_fault_domib_eac(case1_network_line_fault, case1_line_fault_zoomib_eac) -> EAC:
    # Get critical and maximum times with static EAC
    omib_series = OMIBTaylorSeries(case1_line_fault_zoomib_eac.omib)
    angles = [case1_line_fault_zoomib_eac.critical_clearing_angle, case1_line_fault_zoomib_eac.maximum_angle]
    cc_time, max_time = omib_series.get_trajectory_times(angles, case1_line_fault_zoomib_eac.critical_clearing_angle)

    # Update generator angles
    generators = case1_line_fault_zoomib_eac.omib.critical_cluster.generators.union(
        case1_line_fault_zoomib_eac.omib.non_critical_cluster.generators
    )
    generator_series = GeneratorTaylorSeries(case1_network_line_fault)
    generator_series.update_generator_angles(generators, cc_time, max_time, 5, 5)

    # Get critical clusters and create OMIB
    critical_cluster = case1_line_fault_zoomib_eac.omib.critical_cluster
    non_critical_cluster = case1_line_fault_zoomib_eac.omib.non_critical_cluster
    omib = DOMIB(case1_network_line_fault, critical_cluster, non_critical_cluster)

    return EAC(omib, np.pi / 100)


@pytest.fixture
def case1_bus_fault_domib_eac(case1_bus_fault_zoomib_eac, case1_network_bus_fault) -> EAC:
    # Get critical and maximum times with static EAC
    omib_series = OMIBTaylorSeries(case1_bus_fault_zoomib_eac.omib)
    angles = [case1_bus_fault_zoomib_eac.critical_clearing_angle, case1_bus_fault_zoomib_eac.maximum_angle]
    cc_time, max_time = omib_series.get_trajectory_times(angles, case1_bus_fault_zoomib_eac.critical_clearing_angle)

    # Update generator angles
    generators = case1_bus_fault_zoomib_eac.omib.critical_cluster.generators.union(
        case1_bus_fault_zoomib_eac.omib.non_critical_cluster.generators
    )
    generator_series = GeneratorTaylorSeries(case1_network_bus_fault)
    generator_series.update_generator_angles(generators, cc_time, max_time, 4, 4)

    # Get critical clusters and create OMIB
    critical_cluster = case1_bus_fault_zoomib_eac.omib.critical_cluster
    non_critical_cluster = case1_bus_fault_zoomib_eac.omib.non_critical_cluster
    omib = DOMIB(case1_network_bus_fault, critical_cluster, non_critical_cluster)

    return EAC(omib, np.pi / 100)


@pytest.fixture
def basic_domib_eeac_tree() -> EEACTree:
    tree_parser = JSONTreeParser(f"{TEST_DATA_FOLDER}/eeac_trees/basic_domib_tree.json")
    return EEACTreeLoader(tree_parser).load_eeac_tree()


@pytest.fixture
def basic_domib_eeac(basic_domib_eeac_tree, case1_network_line_fault) -> EEAC:
    return EEAC(basic_domib_eeac_tree, case1_network_line_fault)


@pytest.fixture
def basic_eeac_tree() -> EEACTree:
    tree_parser = JSONTreeParser(f"{TEST_DATA_FOLDER}/eeac_trees/basic_tree.json")
    return EEACTreeLoader(tree_parser).load_eeac_tree()


@pytest.fixture
def basic_eeac(basic_eeac_tree, case1_network_line_fault) -> EEAC:
    return EEAC(basic_eeac_tree, case1_network_line_fault)
