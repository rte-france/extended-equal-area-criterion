# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest

from deeac.domain.services.critical_clusters_identifier import ConstrainedCriticalClustersIdentifier
from deeac.domain.exceptions import CriticalClustersIdentifierUnknownGeneratorsException


class TestConstrainedCriticalClustersIdentifier:

    def test_constrained_identifier(self, case1_network_line_fault, case1_line_fault_dynamic_generators):
        identifier = ConstrainedCriticalClustersIdentifier(
            case1_network_line_fault,
            case1_line_fault_dynamic_generators,
            ["GENB1", "GENB2"]
        )
        candidate_clusters = identifier.candidate_clusters
        critical_cluster, non_critical_cluster = next(candidate_clusters)
        assert {generator.name for generator in critical_cluster.generators} == {"GENB1", "GENB2"}
        assert {generator.name for generator in non_critical_cluster.generators} == {"GENA1", "NHVCEQ"}
        critical_cluster, non_critical_cluster = next(candidate_clusters)
        assert {generator.name for generator in critical_cluster.generators} == {"GENB2"}
        assert {generator.name for generator in non_critical_cluster.generators} == {"GENA1", "NHVCEQ", "GENB1"}
        with pytest.raises(StopIteration):
            next(candidate_clusters)

        identifier = ConstrainedCriticalClustersIdentifier(
            case1_network_line_fault,
            case1_line_fault_dynamic_generators,
            ["GENA1"]
        )
        candidate_clusters = identifier.candidate_clusters
        critical_cluster, non_critical_cluster = next(candidate_clusters)
        assert {generator.name for generator in critical_cluster.generators} == {"GENA1"}
        assert {generator.name for generator in non_critical_cluster.generators} == {"GENB1", "GENB2", "NHVCEQ"}
        with pytest.raises(StopIteration):
            next(candidate_clusters)

        with pytest.raises(CriticalClustersIdentifierUnknownGeneratorsException) as e:
            identifier = ConstrainedCriticalClustersIdentifier(
                case1_network_line_fault,
                case1_line_fault_dynamic_generators,
                ["GENB1", "FAKE1", "FAKE2"]
            )
        assert e.value.unknown_generator_names == {"FAKE1", "FAKE2"}
