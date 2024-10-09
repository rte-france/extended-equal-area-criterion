# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import cmath
import numpy as np

from deeac.domain.models import NetworkState, DynamicGenerator
from deeac.domain.services.critical_clusters_identifier import AccelerationCriticalClustersIdentifier
from deeac.domain.models.omib import OMIBStabilityState, ZOOMIB
from deeac.domain.services.eac import EAC
from deeac.domain.models.events import BranchEvent, BreakerPosition, BusShortCircuitEvent


class TestEAC:

    def test_get_trajectory_power_area(self, case1_line_fault_zoomib_eac):
        # ZOOMIB
        acceleration1 = case1_line_fault_zoomib_eac._get_trajectory_power_area(
            case1_line_fault_zoomib_eac.omib.initial_rotor_angle,
            0.6,
            NetworkState.DURING_FAULT
        )
        assert cmath.isclose(acceleration1, 2.9761382807054986, abs_tol=10e-9)

        critical_clearing_angle = case1_line_fault_zoomib_eac.critical_clearing_angle
        acceleration2 = case1_line_fault_zoomib_eac._get_trajectory_power_area(
            0.6,
            critical_clearing_angle,
            NetworkState.DURING_FAULT
        )
        assert cmath.isclose(acceleration2, 2.211857622155085, abs_tol=10e-9)

        acceleration_total = case1_line_fault_zoomib_eac._get_trajectory_power_area(
            case1_line_fault_zoomib_eac.omib.initial_rotor_angle,
            critical_clearing_angle,
            NetworkState.DURING_FAULT
        )
        assert cmath.isclose(acceleration_total, 5.187995902860585, abs_tol=10e-9)

        deceleration1 = case1_line_fault_zoomib_eac._get_trajectory_power_area(
            critical_clearing_angle,
            1.9,
            NetworkState.POST_FAULT
        )
        assert cmath.isclose(deceleration1, -4.314663109230352, abs_tol=10e-9)

        deceleration2 = case1_line_fault_zoomib_eac._get_trajectory_power_area(
            1.9,
            case1_line_fault_zoomib_eac.maximum_angle,
            NetworkState.POST_FAULT
        )
        assert cmath.isclose(deceleration2, -0.8988318667847324, abs_tol=10e-9)

        deceleration_total = case1_line_fault_zoomib_eac._get_trajectory_power_area(
            critical_clearing_angle,
            case1_line_fault_zoomib_eac.maximum_angle,
            NetworkState.POST_FAULT
        )
        assert cmath.isclose(deceleration_total, -5.213494976015084, abs_tol=10e-7)

        # DOMIB
        acceleration1 = case1_line_fault_zoomib_eac._get_trajectory_power_area(
            case1_line_fault_zoomib_eac.omib.initial_rotor_angle,
            0.08,
            NetworkState.DURING_FAULT
        )
        assert cmath.isclose(acceleration1, 0.2586852529161293, abs_tol=10e-9)
        acceleration2 = case1_line_fault_zoomib_eac._get_trajectory_power_area(
            0.08,
            0.12002836197756181,
            NetworkState.DURING_FAULT
        )
        assert cmath.isclose(acceleration2, 0.24502975155972234, abs_tol=10e-9)
        acceleration3 = case1_line_fault_zoomib_eac._get_trajectory_power_area(
            0.12002836197756181,
            0.4712812280610945,
            NetworkState.DURING_FAULT
        )
        assert cmath.isclose(acceleration3, 1.887485041599468, abs_tol=10e-9)
        acceleration4 = case1_line_fault_zoomib_eac._get_trajectory_power_area(
            0.4712812280610945,
            0.9798258745387827,
            NetworkState.DURING_FAULT
        )
        assert cmath.isclose(acceleration4, 2.056469179344025, abs_tol=10e-9)
        acceleration5 = case1_line_fault_zoomib_eac._get_trajectory_power_area(
            0.9798258745387827,
            1.2575917661269675,
            NetworkState.DURING_FAULT
        )
        assert cmath.isclose(acceleration5, 0.9217153461793841, abs_tol=10e-9)

        acceleration_total = case1_line_fault_zoomib_eac._get_power_area(
            case1_line_fault_zoomib_eac.omib.initial_rotor_angle,
            1.2575917661269675,
            NetworkState.DURING_FAULT
        )
        assert cmath.isclose(
            acceleration_total,
            acceleration1 + acceleration2 + acceleration3 + acceleration4 + acceleration5,
            abs_tol=10e-9
        )

        deceleration1 = case1_line_fault_zoomib_eac._get_trajectory_power_area(
            1.2575917661269675,
            1.6551139531039187,
            NetworkState.POST_FAULT
        )
        assert cmath.isclose(deceleration1, -2.66221244506001, abs_tol=10e-9)

        deceleration2 = case1_line_fault_zoomib_eac._get_trajectory_power_area(
            1.6551139531039187,
            2.2943173418115985,
            NetworkState.POST_FAULT
        )
        assert cmath.isclose(deceleration2, -2.1822506543662206, abs_tol=10e-9)

        deceleration_total = case1_line_fault_zoomib_eac._get_power_area(
            1.2575917661269675,
            2.2943173418115985,
            NetworkState.POST_FAULT
        )
        assert cmath.isclose(deceleration_total, deceleration1 + deceleration2, abs_tol=10e-7)

    def test_get_power_area(self, case1_line_fault_domib_eac, case1_line_fault_zoomib_eac):
        # ZOOMIB
        # Acceleration
        acceleration = case1_line_fault_zoomib_eac._get_power_area(
            case1_line_fault_zoomib_eac.omib.initial_rotor_angle,
            1.2,
            NetworkState.DURING_FAULT
        )
        assert cmath.isclose(acceleration, 5.18399702751425, abs_tol=10e-9)

        # Deceleration
        deceleration = case1_line_fault_zoomib_eac._get_power_area(
            case1_line_fault_zoomib_eac.critical_clearing_angle,
            1.5,
            NetworkState.POST_FAULT
        )
        assert cmath.isclose(deceleration, -2.096855019814902, abs_tol=10e-9)

        # DOMIB
        # Acceleration
        acceleration = case1_line_fault_domib_eac._get_power_area(
            case1_line_fault_domib_eac.omib.initial_rotor_angle,
            1.2,
            NetworkState.DURING_FAULT
        )
        assert cmath.isclose(acceleration, 5.2001340534927625, abs_tol=10e-9)

        # Decelerations
        deceleration = case1_line_fault_domib_eac._get_power_area(
            case1_line_fault_domib_eac.critical_clearing_angle,
            1.5,
            NetworkState.POST_FAULT
        )
        assert cmath.isclose(deceleration, -1.8323076891599221, abs_tol=10e-9)

        deceleration = case1_line_fault_domib_eac._get_power_area(
            case1_line_fault_domib_eac.critical_clearing_angle,
            2.2,
            NetworkState.POST_FAULT
        )
        assert cmath.isclose(deceleration, -5.199891755664327, abs_tol=10e-9)
        assert case1_line_fault_domib_eac.omib.stability_state == OMIBStabilityState.POTENTIALLY_STABLE

    def test_always_stable_case(self, case1_network):
        mitigation_events = [
            BranchEvent(
                first_bus_name="NHVA3",
                second_bus_name="NHVD1",
                parallel_id="1",
                breaker_position=BreakerPosition.FIRST_BUS,
                breaker_closed=False
            )
        ]
        case1_network.initialize_simplified_network()
        case1_network.provide_events([], mitigation_events)
        generators = {
            DynamicGenerator(gen) for gen in case1_network.get_state(NetworkState.POST_FAULT).generators
        }
        identifier = AccelerationCriticalClustersIdentifier(case1_network, generators)
        critical_cluster, non_critical_cluster = next(identifier.candidate_clusters)
        omib = ZOOMIB(case1_network, critical_cluster, non_critical_cluster)
        eac = EAC(omib, np.pi / 100)
        assert eac.critical_clearing_angle == 2 * np.pi
        assert eac.maximum_angle == 2 * np.pi
        assert eac.omib.stability_state == OMIBStabilityState.ALWAYS_STABLE

    def test_always_unstable_case(self, case1_network):
        failure_events = [BusShortCircuitEvent("NHVA2")]
        case1_network.initialize_simplified_network()
        case1_network.provide_events(failure_events, [])
        generators = {
            DynamicGenerator(gen) for gen in case1_network.get_state(NetworkState.POST_FAULT).generators
        }
        identifier = AccelerationCriticalClustersIdentifier(case1_network, generators)
        critical_cluster, non_critical_cluster = next(identifier.candidate_clusters)
        omib = ZOOMIB(case1_network, critical_cluster, non_critical_cluster)
        eac = EAC(omib, np.pi / 100)
        assert eac.critical_clearing_angle == omib.initial_rotor_angle
        assert eac.maximum_angle == omib.initial_rotor_angle
        assert eac.omib.stability_state == OMIBStabilityState.ALWAYS_UNSTABLE

    def test_critical_clearing_angle(
        self, case1_line_fault_zoomib_eac, case1_bus_fault_zoomib_eac, case1_line_fault_domib_eac,
        case1_bus_fault_domib_eac, case1_line_fault_coomib_eac
    ):
        assert cmath.isclose(
            case1_line_fault_zoomib_eac.critical_clearing_angle,
            1.201235818096255,
            abs_tol=10e-9
        )
        assert cmath.isclose(
            case1_line_fault_coomib_eac.critical_clearing_angle,
            1.2062939937776758,
            abs_tol=10e-9
        )
        assert cmath.isclose(
            case1_line_fault_domib_eac.critical_clearing_angle,
            1.2377099203135737,
            abs_tol=10e-9
        )
        assert cmath.isclose(
            case1_bus_fault_zoomib_eac.critical_clearing_angle,
            1.169819891560357,
            abs_tol=10e-9
        )
        assert cmath.isclose(
            case1_bus_fault_domib_eac.critical_clearing_angle,
            1.2062939937776758,
            abs_tol=10e-9
        )

    def test_maximum_angle(
        self, case1_line_fault_zoomib_eac, case1_bus_fault_zoomib_eac, case1_line_fault_domib_eac,
        case1_bus_fault_domib_eac, case1_line_fault_coomib_eac
    ):
        assert cmath.isclose(
            case1_line_fault_zoomib_eac.maximum_angle,
            2.2379613937808864,
            abs_tol=10e-9
        )
        assert cmath.isclose(
            case1_line_fault_coomib_eac.maximum_angle,
            2.2430195694623074,
            abs_tol=10e-9
        )
        assert cmath.isclose(
            case1_line_fault_domib_eac.maximum_angle,
            2.274435495998205,
            abs_tol=10e-9
        )
        assert cmath.isclose(
            case1_bus_fault_zoomib_eac.maximum_angle,
            2.269377320316784,
            abs_tol=10e-9
        )
        assert cmath.isclose(
            case1_bus_fault_domib_eac.maximum_angle,
            2.305851422534103,
            abs_tol=10e-9
        )

    def test_omib(self, case1_line_fault_zoomib_eac):
        assert type(case1_line_fault_zoomib_eac.omib) == ZOOMIB
        assert case1_line_fault_zoomib_eac.omib == case1_line_fault_zoomib_eac._omib
