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

from deeac.domain.exceptions import CriticalClustersIdentifierThresholdException
from deeac.domain.services.critical_clusters_identifier import AccelerationCriticalClustersIdentifier


class TestIdentifier:

    def test_init(self, case1_network_line_fault, case1_line_fault_dynamic_generators):
        with pytest.raises(CriticalClustersIdentifierThresholdException):
            AccelerationCriticalClustersIdentifier(case1_network_line_fault, case1_line_fault_dynamic_generators, -1)

    def test_get_generator_initial_acceleration(
        self, acc_cc_identifier, case1_line_fault_dynamic_generators
    ):
        generator = next(gen for gen in case1_line_fault_dynamic_generators if gen.name == "GENA1")
        acc = acc_cc_identifier._get_generator_initial_acceleration(generator)
        assert cmath.isclose(acc, 43.44479293834792, abs_tol=10e-9)

    def test_get_generator_electric_power(
        self, acc_cc_identifier, case1_line_fault_dynamic_generators
    ):
        generator = next(gen for gen in case1_line_fault_dynamic_generators if gen.name == "GENA1")
        electric_power = acc_cc_identifier._get_generator_initial_electric_power(generator)
        assert cmath.isclose(electric_power, 1.6845081464890272, abs_tol=10e-9)

    def test_identify_critical_machine_candidates(
        self, acc_cc_identifier, case1_line_fault_dynamic_generators
    ):
        generators = sorted(list(case1_line_fault_dynamic_generators), key=lambda gen: gen.name)
        criterion_values = [-5.2, 1.9, 10.1, -3.4]
        criterions = []
        for i, generator in enumerate(generators):
            criterions.append((generator, criterion_values[i]))
        acc_cc_identifier._identify_critical_machine_candidates(criterions)
        # Order is important
        critical_names = [gen.name for gen in acc_cc_identifier._critical_machine_candidates]
        assert critical_names == [generators[0].name, generators[2].name]
        acc_cc_identifier._critical_machine_candidates = []

        # Set a power filter (power of 2 first critical generators is 10)
        acc_cc_identifier._min_cluster_power = 11
        acc_cc_identifier._identify_critical_machine_candidates(criterions)
        # Order is important
        critical_names = [gen.name for gen in acc_cc_identifier._critical_machine_candidates]
        assert critical_names == [generators[3].name, generators[0].name, generators[2].name]
        acc_cc_identifier._critical_machine_candidates = []
        acc_cc_identifier._threshold = 0.5

        # Update threshold decrement
        acc_cc_identifier._threshold_decrement = 0.4
        acc_cc_identifier._identify_critical_machine_candidates(criterions)
        # Order is important
        critical_names = [gen.name for gen in acc_cc_identifier._critical_machine_candidates]
        assert critical_names == [generators[1].name, generators[3].name, generators[0].name, generators[2].name]
        acc_cc_identifier._threshold_decrement = 0.1
        acc_cc_identifier._threshold = 0.5
        acc_cc_identifier._critical_machine_candidates = []

        # Min cluster power is very high
        acc_cc_identifier._min_cluster_power = 1000
        acc_cc_identifier._identify_critical_machine_candidates(criterions)
        critical_names = [gen.name for gen in acc_cc_identifier._critical_machine_candidates]
        assert critical_names == [generators[1].name, generators[3].name, generators[0].name, generators[2].name]
        acc_cc_identifier._critical_machine_candidates = []
        acc_cc_identifier._threshold = 0.5
        acc_cc_identifier._min_cluster_power = None

    def test_iterator(self, acc_cc_identifier, case1_line_fault_dynamic_generators):
        generators = list(case1_line_fault_dynamic_generators)
        criterion_values = [5.2, 1.9, 10.1, 6.4]
        criterions = []
        for i, generator in enumerate(generators):
            criterions.append((generator, criterion_values[i]))
        acc_cc_identifier._identify_critical_machine_candidates(criterions)

        # All candidate generators are critical at first step
        candidate_clusters = acc_cc_identifier.candidate_clusters
        critical_cluster, non_critical_cluster = next(candidate_clusters)
        assert {gen.name for gen in critical_cluster.generators} == {
            generators[2].name,
            generators[3].name,
            generators[0].name
        }
        assert {gen.name for gen in non_critical_cluster.generators} == {
            generators[1].name
        }

        # The less critical generator is removed at each step
        critical_cluster, non_critical_cluster = next(candidate_clusters)
        assert {gen.name for gen in critical_cluster.generators} == {
            generators[2].name,
            generators[3].name
        }
        assert {gen.name for gen in non_critical_cluster.generators} == {
            generators[1].name,
            generators[0].name
        }

        critical_cluster, non_critical_cluster = next(candidate_clusters)
        assert {gen.name for gen in critical_cluster.generators} == {
            generators[2].name
        }
        assert {gen.name for gen in non_critical_cluster.generators} == {
            generators[1].name,
            generators[0].name,
            generators[3].name,
        }

        # No more candidates
        with pytest.raises(StopIteration):
            next(candidate_clusters)

    def test_all_combinations(self, acc_cc_identifier, case1_line_fault_dynamic_generators):
        generators = list(case1_line_fault_dynamic_generators)
        criterion_values = [5.2, 1.9, 10.1, 6.4]
        criterions = []
        for i, generator in enumerate(generators):
            criterions.append((generator, criterion_values[i]))
        acc_cc_identifier._try_all_combinations = True
        acc_cc_identifier._identify_critical_machine_candidates(criterions)

        # All candidate generators are critical at first step
        candidate_clusters = [
            (critical_cluster, non_critical_cluster)
            for critical_cluster, non_critical_cluster in acc_cc_identifier.candidate_clusters
        ]
        assert len(candidate_clusters) == 7

    def test_iterator_limit(self, acc_cc_identifier, case1_line_fault_dynamic_generators):
        generators = list(case1_line_fault_dynamic_generators)
        criterion_values = [5.2, 1.9, 10.1, 6.4]
        criterions = []
        for i, generator in enumerate(generators):
            criterions.append((generator, criterion_values[i]))
        acc_cc_identifier._identify_critical_machine_candidates(criterions)
        acc_cc_identifier._maximum_number_candidates = 2

        # All candidate generators are critical at first step
        candidate_clusters = acc_cc_identifier.candidate_clusters
        critical_cluster, non_critical_cluster = next(candidate_clusters)
        assert {gen.name for gen in critical_cluster.generators} == {
            generators[2].name,
            generators[3].name,
            generators[0].name
        }
        assert {gen.name for gen in non_critical_cluster.generators} == {
            generators[1].name
        }

        # The less critical generator is removed
        critical_cluster, non_critical_cluster = next(candidate_clusters)
        assert {gen.name for gen in critical_cluster.generators} == {
            generators[2].name,
            generators[3].name
        }
        assert {gen.name for gen in non_critical_cluster.generators} == {
            generators[1].name,
            generators[0].name
        }

        # Limit reached
        with pytest.raises(StopIteration):
            next(candidate_clusters)

    def test_cluster_candidates(self, acc_cc_identifier, case1_line_fault_dynamic_generators):
        candidate_clusters = acc_cc_identifier.candidate_clusters
        critical_cluster, non_critical_cluster = next(candidate_clusters)
        assert [gen.name for gen in critical_cluster.generators] == ["GENA1"]
        assert {gen.name for gen in non_critical_cluster.generators} == {"GENB1", "GENB2", "NHVCEQ"}
        with pytest.raises(StopIteration):
            next(candidate_clusters)

        # Update criterions
        generators = sorted(list(case1_line_fault_dynamic_generators), key=lambda gen: gen.name)
        criterion_values = [5.2, 1.9, 10.1, 3.4]
        criterions = []
        for i, generator in enumerate(generators):
            criterions.append((generator, criterion_values[i]))
        acc_cc_identifier._identify_critical_machine_candidates(criterions)

        candidate_clusters = acc_cc_identifier.candidate_clusters
        critical_cluster, non_critical_cluster = next(candidate_clusters)
        assert {gen.name for gen in critical_cluster.generators} == {"GENA1", "GENB2"}
        assert {gen.name for gen in non_critical_cluster.generators} == {"GENB1", "NHVCEQ"}
        critical_cluster, non_critical_cluster = next(candidate_clusters)
        assert {gen.name for gen in critical_cluster.generators} == {"GENB2"}
        assert {gen.name for gen in non_critical_cluster.generators} == {"GENA1", "GENB1", "NHVCEQ"}
        with pytest.raises(StopIteration):
            next(candidate_clusters)

        # Set a power filter (power of 2 first critical generators is 10)
        acc_cc_identifier._min_cluster_power = 11
        acc_cc_identifier._identify_critical_machine_candidates(criterions)
        candidate_clusters = acc_cc_identifier.candidate_clusters
        critical_cluster, non_critical_cluster = next(candidate_clusters)
        assert {gen.name for gen in critical_cluster.generators} == {"GENA1", "GENB2", "NHVCEQ"}
        assert {gen.name for gen in non_critical_cluster.generators} == {"GENB1"}
        with pytest.raises(StopIteration):
            next(candidate_clusters)
