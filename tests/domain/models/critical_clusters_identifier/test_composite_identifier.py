# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest
import cmath

from deeac.domain.utils import deepcopy
from deeac.domain.models import NetworkState, DynamicGenerator
from deeac.domain.models.matrices import ImpedanceMatrix
from deeac.domain.models.events import BusShortCircuitEvent, BranchEvent, BreakerPosition
from deeac.domain.services.critical_clusters_identifier import CompositeCriticalClustersIdentifier
from deeac.domain.exceptions import CompositeCriterionException


class TestCompositeCriticalClustersIdentifier:

    def test_get_generator_distance_to_fault(self, comp_cc_identifier, case1_network_line_fault):
        with pytest.raises(CompositeCriterionException):
            # This criterion can not be applied in cas of multiple faults
            network = deepcopy(case1_network_line_fault)
            network.provide_events(
                [
                    BusShortCircuitEvent("NHVA1"),
                    BusShortCircuitEvent("NHVA2")
                ],
                [
                    BranchEvent("NHVA1", "NHVA2", "1", BreakerPosition.FIRST_BUS)
                ],
            )
            dynamic_generators = [DynamicGenerator(generator) for generator in network.generators]
            CompositeCriticalClustersIdentifier(network, dynamic_generators)

        failure_bus = next(bus for bus in case1_network_line_fault.buses if bus.name == "NHVA3")
        generator = case1_network_line_fault.get_state(NetworkState.POST_FAULT).generators[0]
        pre_fault_imp_matrix = ImpedanceMatrix(
            case1_network_line_fault.get_state(NetworkState.PRE_FAULT).admittance_matrix
        )
        distance = comp_cc_identifier._get_generator_distance_to_fault(generator, failure_bus, pre_fault_imp_matrix)
        assert cmath.isclose(distance, 0.03785470114434578, abs_tol=10e-9)

    def test_compute_criterions(
        self, comp_cc_identifier, case1_network_line_fault, case1_line_fault_dynamic_generators
    ):
        expected_criterions = {
            next(gen for gen in case1_line_fault_dynamic_generators if gen.name == "GENA1"): 492.81651134181556,
            next(gen for gen in case1_line_fault_dynamic_generators if gen.name == "GENB1"): 76.23455846475952,
            next(gen for gen in case1_line_fault_dynamic_generators if gen.name == "GENB2"): 17.767444784097638,
            next(gen for gen in case1_line_fault_dynamic_generators if gen.name == "NHVCEQ"): 11.114047270134837
        }
        criterions = comp_cc_identifier._compute_criterions()
        for (gen, criterion) in criterions:
            assert cmath.isclose(criterion, expected_criterions[gen], abs_tol=10e-9)

    def test_cluster_candidates(self, comp_cc_identifier):
        candidate_clusters = comp_cc_identifier.candidate_clusters
        critical_cluster, non_critical_cluster = next(candidate_clusters)
        assert [gen.name for gen in critical_cluster.generators] == ["GENA1"]
        assert {gen.name for gen in non_critical_cluster.generators} == {"GENB1", "GENB2", "NHVCEQ"}
        with pytest.raises(StopIteration):
            next(candidate_clusters)
