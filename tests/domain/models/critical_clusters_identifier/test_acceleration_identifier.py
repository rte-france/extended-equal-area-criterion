# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import cmath
import pytest


class TestAccelerationCriticalClustersIdentifier:

    def test_compute_criterions(self, acc_cc_identifier, case1_network_line_fault, case1_line_fault_dynamic_generators):
        expected_criterions = {
            next(gen for gen in case1_line_fault_dynamic_generators if gen.name == "GENA1"): 43.444792938347916,
            next(gen for gen in case1_line_fault_dynamic_generators if gen.name == "GENB1"): 18.01733599493662,
            next(gen for gen in case1_line_fault_dynamic_generators if gen.name == "GENB2"): 16.29470089193051,
            next(gen for gen in case1_line_fault_dynamic_generators if gen.name == "NHVCEQ"): 0.5405001688099794
        }
        criterions = acc_cc_identifier._compute_criterions()
        for (gen, criterion) in criterions:
            assert cmath.isclose(criterion, expected_criterions[gen], abs_tol=10e-9)

    def test_cluster_candidates(self, acc_cc_identifier):
        candidate_clusters = acc_cc_identifier.candidate_clusters
        critical_cluster, non_critical_cluster = next(candidate_clusters)
        assert [gen.name for gen in critical_cluster.generators] == ["GENA1"]
        assert {gen.name for gen in non_critical_cluster.generators} == {"GENB1", "GENB2", "NHVCEQ"}
        with pytest.raises(StopIteration):
            next(candidate_clusters)
