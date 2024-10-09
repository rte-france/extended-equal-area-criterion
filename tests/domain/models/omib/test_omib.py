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

from deeac.domain.models import NetworkState, GeneratorCluster
from deeac.domain.exceptions import UnknownRotorAngleException
from deeac.domain.models.omib.omib import OMIBStabilityState, OMIBSwingState


class TestOmib:

    def test_repr(self, case1_zoomib, case1_domib):
        assert repr(case1_zoomib) == (
            "OMIB:\n"
            "\tType: ZOOMIB\n"
            "\tStability state: UNKNOWN\n"
            "\tSwing state: FORWARD\n"
            "\tCritical generators: GENA1\n"
            "\tProperties:\n"
            "\t\tPRE-FAULT:\n"
            "\t\t\tAngle: 0.039 rad [2.226 deg] - Time: 0 ms - Angle shift: -0.365 rad "
            "[-20.909 deg] - Constant power: 2.883 p.u. - Maximum power: 14.896 p.u.\n"
            "\t\tDURING-FAULT:\n"
            "\t\t\tAngle: 0.039 rad [2.226 deg] - Time: 0 ms - Angle shift: -0.21 rad "
            "[-12.005 deg] - Constant power: 1.326 p.u. - Maximum power: 4.228 p.u.\n"
            "\t\tPOST-FAULT:\n"
            "\t\t\tAngle: 0.039 rad [2.226 deg] - Time: 0 ms - Angle shift: -0.392 rad "
            "[-22.455 deg] - Constant power: 3.71 p.u. - Maximum power: 12.269 p.u."
        )

        assert repr(case1_domib) == (
             "OMIB:\n"
             "\tType: DOMIB\n"
             "\tStability state: UNKNOWN\n"
             "\tSwing state: FORWARD\n"
             "\tCritical generators: GENA1\n"
             "\tProperties:\n"
             "\t\tPRE-FAULT:\n"
             "\t\t\tAngle: 0.044 rad [2.516 deg] - Time: 0 ms - Angle shift: -0.36 rad "
             "[-20.614 deg] - Constant power: 2.883 p.u. - Maximum power: 14.899 p.u.\n"
             "\t\tDURING-FAULT:\n"
             "\t\t\tAngle: 0.044 rad [2.516 deg] - Time: 0 ms - Angle shift: -0.207 rad "
             "[-11.888 deg] - Constant power: 1.326 p.u. - Maximum power: 4.229 p.u.\n"
             "\t\t\tAngle: 0.093 rad [5.324 deg] - Time: 106.928 ms - Angle shift: -0.202 "
             "rad [-11.552 deg] - Constant power: 1.326 p.u. - Maximum power: 4.229 p.u.\n"
             "\t\t\tAngle: 0.376 rad [21.544 deg] - Time: 160.392 ms - Angle shift: -0.194 "
             "rad [-11.143 deg] - Constant power: 1.326 p.u. - Maximum power: 4.227 p.u.\n"
             "\t\t\tAngle: 0.747 rad [42.777 deg] - Time: 213.856 ms - Angle shift: -0.185 "
             "rad [-10.599 deg] - Constant power: 1.326 p.u. - Maximum power: 4.217 p.u.\n"
             "\t\tPOST-FAULT:\n"
             "\t\t\tAngle: 0.044 rad [2.516 deg] - Time: 0 ms - Angle shift: -0.388 rad "
             "[-22.229 deg] - Constant power: 3.71 p.u. - Maximum power: 12.274 p.u.\n"
             "\t\t\tAngle: 1.186 rad [67.981 deg] - Time: 267.32 ms - Angle shift: -0.322 "
             "rad [-18.465 deg] - Constant power: 3.716 p.u. - Maximum power: 12.127 p.u.\n"
             "\t\t\tAngle: 1.562 rad [89.51 deg] - Time: 315.615 ms - Angle shift: -0.304 "
             "rad [-17.396 deg] - Constant power: 3.72 p.u. - Maximum power: 11.993 p.u.\n"
             "\t\t\tAngle: 1.849 rad [105.928 deg] - Time: 363.909 ms - Angle shift: -0.29 "
             "rad [-16.589 deg] - Constant power: 3.724 p.u. - Maximum power: 11.854 p.u.\n"
             "\t\t\tAngle: 2.066 rad [118.36 deg] - Time: 412.204 ms - Angle shift: -0.28 "
             "rad [-16.026 deg] - Constant power: 3.728 p.u. - Maximum power: 11.731 p.u.\n"
             "\t\t\tAngle: 2.235 rad [128.082 deg] - Time: 460.498 ms - Angle shift: "
             "-0.274 rad [-15.673 deg] - Constant power: 3.73 p.u. - Maximum power: 11.638 "
             "p.u.\n"
             "\t\t\tAngle: 2.379 rad [136.296 deg] - Time: 508.793 ms - Angle shift: -0.27 "
             "rad [-15.491 deg] - Constant power: 3.731 p.u. - Maximum power: 11.585 p.u."
        )

    def test_network(self, case1_zoomib, case1_network_line_fault):
        assert case1_zoomib.network == case1_network_line_fault

    def test_critical_cluster(self, case1_zoomib):
        assert type(case1_zoomib.critical_cluster) == GeneratorCluster
        assert {gen.name for gen in case1_zoomib.critical_cluster.generators} == {"GENA1"}

    def test_swing_state(self, case1_zoomib):
        assert case1_zoomib.swing_state == OMIBSwingState.FORWARD

    def test_stability_state(self, case1_zoomib):
        assert case1_zoomib.stability_state == OMIBStabilityState.UNKNOWN
        # Set a new state
        case1_zoomib.stability_state = OMIBStabilityState.ALWAYS_STABLE
        assert case1_zoomib.stability_state == OMIBStabilityState.ALWAYS_STABLE

    def test_non_critical_cluster(self, case1_zoomib):
        assert type(case1_zoomib.non_critical_cluster) == GeneratorCluster
        assert {gen.name for gen in case1_zoomib.non_critical_cluster.generators} == {"GENB1", "GENB2", "NHVCEQ"}

    def test_mechanical_power(self, case1_zoomib):
        assert cmath.isclose(case1_zoomib.mechanical_power, 8.735081018322676, abs_tol=10e-9)

    def test_update_angles(self, case1_domib, case1_zoomib):
        update_angles = case1_zoomib.update_angles
        assert update_angles == [
            (case1_zoomib.initial_rotor_angle, 0, NetworkState.PRE_FAULT),
            (case1_zoomib.initial_rotor_angle, 0, NetworkState.DURING_FAULT),
            (case1_zoomib.initial_rotor_angle, 0, NetworkState.POST_FAULT)
        ]

        # First update in during-fault state is associated to a decreasing angle
        update_angles = case1_domib.update_angles
        expected_update_angles = [
            (0.04390471194945145, 0, NetworkState.PRE_FAULT),
            (0.04390471194945145, 0, NetworkState.DURING_FAULT),
            (0.04390471194945145, 0, NetworkState.POST_FAULT),
            (0.09291368534078437, 0.10692814597180633, NetworkState.DURING_FAULT),
            (0.376011668674103, 0.1603922189577095, NetworkState.DURING_FAULT),
            (0.7466052151708675, 0.21385629194361266, NetworkState.DURING_FAULT),
            (1.1864985938166717, 0.26732036492951583, NetworkState.POST_FAULT),
            (1.5622526370244552, 0.3156147942844886, NetworkState.POST_FAULT),
            (1.8487870107960198, 0.3639092236394614, NetworkState.POST_FAULT),
            (2.0657790510339615, 0.4122036529944341, NetworkState.POST_FAULT),
            (2.2354575422496783, 0.4604980823494069, NetworkState.POST_FAULT),
            (2.3788092480125034, 0.5087925117043797, NetworkState.POST_FAULT)
        ]
        assert len(update_angles) == len(expected_update_angles)
        for i, angle in enumerate(update_angles):
            assert cmath.isclose(angle[0], expected_update_angles[i][0], abs_tol=10e-9)
            assert cmath.isclose(angle[1], expected_update_angles[i][1], abs_tol=10e-9)
            assert angle[2] == expected_update_angles[i][2]

    def test_get_update_angle(self, case1_domib, case1_zoomib):
        # ZOOMIB should always return initial angle
        update_angle = case1_zoomib._get_update_angle(case1_zoomib.initial_rotor_angle, NetworkState.PRE_FAULT)
        assert update_angle == (case1_zoomib.initial_rotor_angle, 0, NetworkState.PRE_FAULT)
        update_angle = case1_zoomib._get_update_angle(case1_zoomib.initial_rotor_angle, NetworkState.DURING_FAULT)
        assert update_angle == (case1_zoomib.initial_rotor_angle, 0, NetworkState.DURING_FAULT)
        update_angle = case1_zoomib._get_update_angle(0.5, NetworkState.DURING_FAULT)
        assert update_angle == (case1_zoomib.initial_rotor_angle, 0, NetworkState.DURING_FAULT)
        update_angle = case1_zoomib._get_update_angle(0.6, NetworkState.POST_FAULT)
        assert update_angle == (case1_zoomib.initial_rotor_angle, 0, NetworkState.POST_FAULT)

        # DOMIB
        update_angle = case1_domib._get_update_angle(case1_domib.initial_rotor_angle, NetworkState.PRE_FAULT)
        assert update_angle == (case1_domib.initial_rotor_angle, 0, NetworkState.PRE_FAULT)
        update_angle = case1_domib._get_update_angle(case1_domib.initial_rotor_angle, NetworkState.DURING_FAULT)
        assert update_angle == (case1_domib.initial_rotor_angle, 0, NetworkState.DURING_FAULT)
        # Initial angle is not considered for post-fault state, use first update point
        update_angle = case1_domib._get_update_angle(case1_domib.initial_rotor_angle, NetworkState.POST_FAULT)
        assert cmath.isclose(update_angle[0], 1.1864985938166717, abs_tol=10e-9)
        assert cmath.isclose(update_angle[1], 0.26732036492951583, abs_tol=10e-9)
        assert update_angle[2] == NetworkState.POST_FAULT
        # Point before first update angle returns first update
        assert update_angle == case1_domib._get_update_angle(1.5, NetworkState.POST_FAULT)
        # Point between second and third post-fault updates
        update_angle = case1_domib._get_update_angle(2.5, NetworkState.POST_FAULT)
        assert cmath.isclose(update_angle[0], 2.3788092480125034, abs_tol=10e-9)
        assert cmath.isclose(update_angle[1], 0.5087925117043797, abs_tol=10e-9)
        assert update_angle[2] == NetworkState.POST_FAULT
        # Point after last post-fault updates
        update_angle = case1_domib._get_update_angle(8, NetworkState.POST_FAULT)
        assert cmath.isclose(update_angle[0], 2.3788092480125034, abs_tol=10e-9)
        assert cmath.isclose(update_angle[1], 0.5087925117043797, abs_tol=10e-9)
        assert update_angle[2] == NetworkState.POST_FAULT
        # Point between second and third during-fault updates
        update_angle = case1_domib._get_update_angle(0.2, NetworkState.DURING_FAULT)
        assert cmath.isclose(update_angle[0], 0.09291368534078437, abs_tol=10e-9)
        assert cmath.isclose(update_angle[1], 0.10692814597180633, abs_tol=10e-9)
        assert update_angle[2] == NetworkState.DURING_FAULT
        # Point after last during-fault update
        update_angle = case1_domib._get_update_angle(1.5, NetworkState.DURING_FAULT)
        assert cmath.isclose(update_angle[0], 0.7466052151708675, abs_tol=10e-9)
        assert cmath.isclose(update_angle[1], 0.21385629194361266, abs_tol=10e-9)
        assert update_angle[2] == NetworkState.DURING_FAULT

    def test_get_electric_power(self, case1_zoomib):
        power = case1_zoomib.get_electric_power(0.5, NetworkState.DURING_FAULT)
        assert cmath.isclose(power, 4.080202873547963, abs_tol=10e-9)
        power = case1_zoomib.get_electric_power(0.5, NetworkState.POST_FAULT)
        assert cmath.isclose(power, 13.258628327836675, abs_tol=10e-9)

    def test_get_properties(self, case1_zoomib):
        angle_shift, constant_electric_power, maximum_electric_power = case1_zoomib.get_properties(
            NetworkState.PRE_FAULT
        )
        assert cmath.isclose(constant_electric_power, 2.8828073577774185, abs_tol=10e-9)
        assert cmath.isclose(maximum_electric_power, 14.895545159024437, abs_tol=10e-9)
        assert cmath.isclose(angle_shift, -0.3649229680915033, abs_tol=10e-9)

    def test_get_rotor_angle_at_time(self, case1_domib, case1_line_fault_dynamic_generators_updated):
        time = list(list(case1_line_fault_dynamic_generators_updated)[0]._rotor_angles.keys())[2]
        assert cmath.isclose(case1_domib._get_rotor_angle_at_time(
            time,
            NetworkState.DURING_FAULT),
            0.09291368534078437, abs_tol=10e-9)
        with pytest.raises(UnknownRotorAngleException):
            # Generator rotor angles not updated at this time
            case1_domib._get_rotor_angle_at_time(4, NetworkState.DURING_FAULT)
