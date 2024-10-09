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

from deeac.domain.services.critical_clusters_identifier import DuringFaultTrajectoryCriticalClustersIdentifier


class TestDuringFaultTrajectoryCriticalClustersIdentifier:

    def test_compute_angle_variation_list(
        self, during_fault_cc_identifier, case1_network_line_fault, case1_line_fault_dynamic_generators_updated
    ):
        expected_variations = {
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "GENA1"): 35.77373730884357,
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "GENB1"): 15.37198440372555,
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "GENB2"): 13.931049141807845,
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "NHVCEQ"): 0.4935383558089571
        }
        angle_variation_list = during_fault_cc_identifier._compute_angle_variation_list()
        for gen, angle_variation in zip(case1_line_fault_dynamic_generators_updated, angle_variation_list):
            assert cmath.isclose(angle_variation, expected_variations[gen], abs_tol=10e-9)

        # Tries with angles at critical clearing time
        identifier = DuringFaultTrajectoryCriticalClustersIdentifier(
            network=case1_network_line_fault,
            generators=case1_line_fault_dynamic_generators_updated,
            maximum_number_candidates=0,
            during_fault_identification_time_step=175
        )
        expected_variations = {
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "GENA1"): 35.77373730884357,
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "GENB1"): 15.37198440372555,
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "GENB2"): 13.931049141807845,
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "NHVCEQ"): 0.4935383558089571
        }
        angle_variation_list = identifier._compute_angle_variation_list()

        for gen, angle_variation in zip(case1_line_fault_dynamic_generators_updated, angle_variation_list):
            assert cmath.isclose(angle_variation, expected_variations[gen], abs_tol=10e-9)

    def test_cluster_candidates(self, during_fault_cc_identifier):
        clusters = during_fault_cc_identifier.candidate_clusters
        critical_cluster, non_critical_cluster = next(clusters)
        assert {gen.name for gen in critical_cluster.generators} == {"GENA1"}
        assert {gen.name for gen in non_critical_cluster.generators} == {"NHVCEQ", "GENB2", "GENB1"}
        with pytest.raises(StopIteration):
            next(clusters)

    def test_power_matrices_and_angle_derivatives(self, during_fault_cc_identifier):
        matrix_a, matrix_b = during_fault_cc_identifier._get_power_matrices()
        # The order is randomly determined at execution
        # If the total sum is equal at 10-9 then the matrices can be supposed identical
        assert cmath.isclose(sum(sum(row) for row in matrix_a), 14.218926108593696, abs_tol=10e-9)
        assert cmath.isclose(sum(sum(row) for row in matrix_b), 67.84370651067908, abs_tol=10e-9)

        d2_list, d4_list = during_fault_cc_identifier._get_angle_derivatives(matrix_a, matrix_b)
        # Same logic here the order doesn't matter
        assert cmath.isclose(sum(d2_list), 78.29732999402505, abs_tol=10e-9)
        assert cmath.isclose(sum(d4_list), -1394.8768049153257, abs_tol=10e-9)
