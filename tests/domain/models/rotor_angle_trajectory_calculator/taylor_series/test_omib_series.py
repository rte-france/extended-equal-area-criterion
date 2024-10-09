# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import cmath

from deeac.domain.models import NetworkState
from deeac.domain.models.rotor_angle_trajectory_calculator import OMIBTrajectoryAngle, OMIBTrajectoryPoint
from deeac.domain.models.rotor_angle_trajectory_calculator.taylor_series import OMIBTaylorSeries


class TestOMIBTaylorSeries:

    def test_get_angular_speed_derivatives(self, case1_line_fault_omib_taylor_series, case1_domib):
        # No OMIB update
        series = case1_line_fault_omib_taylor_series
        angular_speed = 0.0222302585228561
        angle = 1.2344784642121742
        derivatives = series._get_angular_speed_derivatives(angular_speed, angle, NetworkState.POST_FAULT)
        expected_values = (-0.1375226437412828, 0.09062682482658545, 10.811931587523748, -215.11263050338067)
        for i, derivative in enumerate(derivatives):
            assert cmath.isclose(derivative, expected_values[i], abs_tol=10e-9)

        # OMIB updates
        series = OMIBTaylorSeries(case1_domib)
        angular_speed = 0.0222302585228561
        angle = 1.2344784642121742
        derivatives = series._get_angular_speed_derivatives(angular_speed, angle, NetworkState.POST_FAULT)
        expected_values = (-0.1352753991594668, -0.022623992242684833, 11.39487491888322, -204.38025899728146)
        for i, derivative in enumerate(derivatives):
            assert cmath.isclose(derivative, expected_values[i], abs_tol=10e-9)

    def test_get_trajectory_point(
        self, case1_line_fault_omib_taylor_series, case1_line_fault_zoomib_eac, case1_line_fault_domib_eac
    ):
        # No OMIB update
        series = case1_line_fault_omib_taylor_series
        omib = series._omib
        initial_point = OMIBTrajectoryPoint(
            network_state=NetworkState.DURING_FAULT,
            time=0,
            angle=omib.initial_rotor_angle,
            angular_speed=0
        )

        # First point before the critical one
        rotor_angle = OMIBTrajectoryAngle(
            network_state=NetworkState.DURING_FAULT,
            angle=1
        )
        first_point = series._get_trajectory_point(
            from_point=initial_point,
            to_angle=rotor_angle
        )
        assert cmath.isclose(first_point.time, 0.23902167274812414, abs_tol=10e-9)
        assert cmath.isclose(first_point.angle, rotor_angle.angle, abs_tol=10e-9)
        assert cmath.isclose(first_point.angular_speed, 0.0222184328645004, abs_tol=10e-9)
        assert first_point.network_state == NetworkState.DURING_FAULT

        # Compute critical clearing point from initial point
        critical_rotor_angle = OMIBTrajectoryAngle(
            network_state=NetworkState.POST_FAULT,
            angle=case1_line_fault_zoomib_eac.critical_clearing_angle
        )
        critical_point = series._get_trajectory_point(
            from_point=initial_point,
            to_angle=critical_rotor_angle
        )
        assert cmath.isclose(critical_point.time, 0.26732036492951583, abs_tol=10e-9)
        assert cmath.isclose(critical_point.angle, critical_rotor_angle.angle, abs_tol=10e-9)
        assert cmath.isclose(critical_point.angular_speed, 0.022952054374098172, abs_tol=10e-9)
        assert critical_point.network_state == NetworkState.POST_FAULT

        # Compute critical clearing point from previous point (should be close to previous result)
        critical_point = series._get_trajectory_point(
            from_point=first_point,
            to_angle=critical_rotor_angle
        )
        assert cmath.isclose(critical_point.time, 0.2667427615410016, abs_tol=10e-9)
        assert cmath.isclose(critical_point.angle, critical_rotor_angle.angle, abs_tol=10e-9)
        assert cmath.isclose(critical_point.angular_speed, 0.023976854907585988, abs_tol=10e-9)
        assert critical_point.network_state == NetworkState.POST_FAULT

        # Get angle between critical and maximum ones
        angle = OMIBTrajectoryAngle(
            network_state=NetworkState.POST_FAULT,
            angle=1.8
        )
        point_p = series._get_trajectory_point(
            from_point=critical_point,
            to_angle=angle
        )
        assert cmath.isclose(point_p.time, 0.3779314872199212, abs_tol=10e-9)
        assert cmath.isclose(point_p.angle, angle.angle, abs_tol=10e-9)
        assert cmath.isclose(point_p.angular_speed, 0.01040983915602383, abs_tol=10e-9)
        assert point_p.network_state == NetworkState.POST_FAULT

        # Get angle at maximum time from previous angle
        angle = OMIBTrajectoryAngle(
            network_state=NetworkState.POST_FAULT,
            angle=case1_line_fault_zoomib_eac.maximum_angle
        )
        max_point = series._get_trajectory_point(
            from_point=point_p,
            to_angle=angle
        )
        assert cmath.isclose(max_point.time, 0.7815869331468266, abs_tol=10e-9)
        assert cmath.isclose(max_point.angle, angle.angle, abs_tol=10e-9)
        assert cmath.isclose(max_point.angular_speed, -0.05859296400704256, abs_tol=10e-9)
        assert max_point.network_state == NetworkState.POST_FAULT

        # Get angle at maximum time from critical angle
        max_point = series._get_trajectory_point(
            from_point=critical_point,
            to_angle=angle
        )
        assert cmath.isclose(max_point.time, 0.4878511037587831, abs_tol=10e-9)
        assert cmath.isclose(max_point.angle, angle.angle, abs_tol=10e-9)
        assert cmath.isclose(max_point.angular_speed, -0.005043291695904454, abs_tol=10e-9)
        assert max_point.network_state == NetworkState.POST_FAULT

        # DOMIB
        series = OMIBTaylorSeries(case1_line_fault_domib_eac.omib)
        omib = series._omib
        initial_point = OMIBTrajectoryPoint(
            network_state=NetworkState.DURING_FAULT,
            time=0,
            angle=omib.initial_rotor_angle,
            angular_speed=0
        )

        # First point
        rotor_angle = OMIBTrajectoryAngle(
            network_state=NetworkState.DURING_FAULT,
            angle=0.10
        )
        first_point = series._get_trajectory_point(
            from_point=initial_point,
            to_angle=rotor_angle
        )
        assert cmath.isclose(first_point.time, 0.054489652489641965, abs_tol=10e-9)
        assert cmath.isclose(first_point.angle, rotor_angle.angle, abs_tol=10e-9)
        assert cmath.isclose(first_point.angular_speed, 0.006513830676224789, abs_tol=10e-9)
        assert first_point.network_state == NetworkState.DURING_FAULT
