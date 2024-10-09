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

from deeac.domain.services.critical_clusters_identifier import TrajectoryCriticalClustersIdentifier


class TestTrajectoryCriticalClustersIdentifier:

    def test_compute_angle_variation_list(
        self, trajectory_cc_identifier, case1_network_line_fault, case1_line_fault_dynamic_generators_updated
    ):
        expected_variations = {
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "GENA1"): 2.622866421053712,
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "GENB1"): 1.247383003798899,
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "GENB2"): 1.1431431099944962,
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "NHVCEQ"): 0.08782940985830096
        }
        angle_variation_list = trajectory_cc_identifier._compute_angle_variation_list()
        for gen, angle_variation in zip(case1_line_fault_dynamic_generators_updated, angle_variation_list):
            assert cmath.isclose(angle_variation, expected_variations[gen], abs_tol=10e-9)

        # Tries with angles at critical clearing time
        identifier = TrajectoryCriticalClustersIdentifier(
            network=case1_network_line_fault,
            generators=case1_line_fault_dynamic_generators_updated,
            maximum_number_candidates=0,
            observation_moment_id=4
        )
        expected_variations = {
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "GENA1"): 0.9089464753994045,
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "GENB1"): 0.39579513673724476,
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "GENB2"): 0.3589280701683375,
            next(gen for gen in case1_line_fault_dynamic_generators_updated if gen.name == "NHVCEQ"): 0.013110172892046856
        }
        angle_variation_list = identifier._compute_angle_variation_list()
        for gen, angle_variation in zip(case1_line_fault_dynamic_generators_updated, angle_variation_list):
            assert cmath.isclose(angle_variation, expected_variations[gen], abs_tol=10e-9)

    def test_cluster_candidates(self, trajectory_cc_identifier):
        clusters = trajectory_cc_identifier.candidate_clusters
        critical_cluster, non_critical_cluster = next(clusters)
        assert {gen.name for gen in critical_cluster.generators} == {"GENA1"}
        assert {gen.name for gen in non_critical_cluster.generators} == {"NHVCEQ", "GENB2", "GENB1"}
        with pytest.raises(StopIteration):
            next(clusters)
