# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.domain.models import DynamicGenerator, NetworkState
from deeac.domain.services.critical_clusters_identifier import (
    AccelerationCriticalClustersIdentifier, CompositeCriticalClustersIdentifier, TrajectoryCriticalClustersIdentifier,
    ConstrainedCriticalClustersIdentifier, DuringFaultTrajectoryCriticalClustersIdentifier
)
from deeac.domain.services.factories import CriticalClustersIdentifierFactory


class TestCriticalClustersIdentifierFactory:

    def test_get_identifier(self, case1_network_line_fault):
        generators = [
            DynamicGenerator(gen) for gen in case1_network_line_fault.get_state(NetworkState.POST_FAULT).generators
        ]
        identifier = CriticalClustersIdentifierFactory.get_identifier(
            network=case1_network_line_fault,
            generators=generators,
            cc_identifier_type=AccelerationCriticalClustersIdentifier,
        )
        assert type(identifier) == AccelerationCriticalClustersIdentifier
        assert identifier._network == case1_network_line_fault

        identifier = CriticalClustersIdentifierFactory.get_identifier(
            network=case1_network_line_fault,
            generators=generators,
            cc_identifier_type=CompositeCriticalClustersIdentifier,
            threshold=0.8
        )
        assert type(identifier) == CompositeCriticalClustersIdentifier
        assert identifier._network == case1_network_line_fault
        assert identifier._threshold == 0.8
        assert identifier._min_cluster_power is None
        assert identifier._threshold_decrement == 0.1

        identifier = CriticalClustersIdentifierFactory.get_identifier(
            network=case1_network_line_fault,
            generators=generators,
            cc_identifier_type=TrajectoryCriticalClustersIdentifier,
            min_cluster_power=10,
            observation_moment_id=0
        )
        assert type(identifier) == TrajectoryCriticalClustersIdentifier
        assert identifier._observation_moment_id == 0
        assert identifier._min_cluster_power == 10

        identifier = CriticalClustersIdentifierFactory.get_identifier(
            network=case1_network_line_fault,
            generators=generators,
            cc_identifier_type=DuringFaultTrajectoryCriticalClustersIdentifier,
            maximum_number_candidates=3,
            during_fault_identification_time_step=175,
            during_fault_identification_plot_times=None,
        )
        assert type(identifier) == DuringFaultTrajectoryCriticalClustersIdentifier
        assert identifier._maximum_number_candidates == 3
        assert identifier._during_fault_identification_time_step == 175
        assert identifier._during_fault_identification_plot_times is None

        identifier = CriticalClustersIdentifierFactory.get_identifier(
            network=case1_network_line_fault,
            generators=generators,
            cc_identifier_type=ConstrainedCriticalClustersIdentifier,
            threshold=0.6,
            critical_generator_names={"GENB1"},
            maximum_number_candidates=3
        )
        assert type(identifier) == ConstrainedCriticalClustersIdentifier
        generators = next(identifier.candidate_clusters)[0].generators
        assert len(generators) == 1
        next(iter(generators)).name == "GENB1"
        assert identifier._maximum_number_candidates == 3
