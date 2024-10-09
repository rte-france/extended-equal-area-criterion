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
from deeac.domain.models.rotor_angle_trajectory_calculator.numerical_integrator import OMIBNumericalIntegrator
from deeac.domain.models.rotor_angle_trajectory_calculator.numerical_integrator.omib_integrator import _swing_equation


class TestOMIBNumericalIntegrator:

    def test_swing_equation(self, case1_line_fault_omib_numerical_integrator, case1_line_fault_zoomib_eac):
        omib = case1_line_fault_omib_numerical_integrator.omib
        initial_angle = omib.initial_rotor_angle

        # Initial point
        speed, speed_der = _swing_equation(0, (initial_angle, 0), omib, NetworkState.DURING_FAULT, initial_angle)
        assert speed == 0
        assert cmath.isclose(speed_der, 0.12124862757443461, abs_tol=10e-9)

        # Critical point
        critical_angle = case1_line_fault_zoomib_eac.critical_clearing_angle
        speed, speed_der = _swing_equation(
            0.27178361983020694, (critical_angle, 0.02225942487878904), omib, NetworkState.POST_FAULT, critical_angle
        )
        assert cmath.isclose(speed, 6.993004567233752, abs_tol=10e-9)
        assert cmath.isclose(speed_der, -0.1378251199202701, abs_tol=10e-9)

    def test_get_trajectory_point(
        self, case1_line_fault_omib_numerical_integrator, case1_line_fault_zoomib_eac, case1_line_fault_domib_eac
    ):
        # No OMIB update
        series = case1_line_fault_omib_numerical_integrator
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
        assert cmath.isclose(first_point.time, 0.23685298964715085, abs_tol=10e-9)
        assert cmath.isclose(first_point.angle, rotor_angle.angle, abs_tol=10e-9)
        assert cmath.isclose(first_point.angular_speed, 0.02340414878131787, abs_tol=10e-9)
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
        assert cmath.isclose(critical_point.time, 0.2632595172435544, abs_tol=10e-9)
        assert cmath.isclose(critical_point.angle, critical_rotor_angle.angle, abs_tol=10e-9)
        assert cmath.isclose(critical_point.angular_speed, 0.025081177296286217, abs_tol=10e-9)
        assert critical_point.network_state == NetworkState.POST_FAULT

        # Compute critical clearing point from previous point (should be close to previous result)
        critical_point = series._get_trajectory_point(
            from_point=first_point,
            to_angle=critical_rotor_angle
        )
        assert cmath.isclose(critical_point.time, 0.26322680663685294, abs_tol=10e-9)
        assert cmath.isclose(critical_point.angle, critical_rotor_angle.angle, abs_tol=10e-9)
        assert cmath.isclose(critical_point.angular_speed, 0.02508008280283949, abs_tol=10e-9)
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
        assert cmath.isclose(point_p.time, 0.36624586095790573, abs_tol=10e-9)
        assert cmath.isclose(point_p.angle, angle.angle, abs_tol=10e-9)
        assert cmath.isclose(point_p.angular_speed, 0.012725876497291072, abs_tol=10e-9)
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
        assert cmath.isclose(max_point.time, 2.0423117, abs_tol=10e-6)
        assert cmath.isclose(max_point.angle, angle.angle, abs_tol=10e-9)
        assert cmath.isclose(max_point.angular_speed, 0.0003931601359871458, abs_tol=10e-9)
        assert max_point.network_state == NetworkState.POST_FAULT

        # Get angle at maximum time from critical angle
        max_point = series._get_trajectory_point(
            from_point=critical_point,
            to_angle=angle
        )
        assert cmath.isclose(max_point.time, 6.2425007107446975, abs_tol=10e-5)
        assert cmath.isclose(max_point.angle, angle.angle, abs_tol=10e-9)
        assert cmath.isclose(max_point.angular_speed, 0.0016133967746811764, abs_tol=10e-5)
        assert max_point.network_state == NetworkState.POST_FAULT

        # DOMIB
        series = OMIBNumericalIntegrator(case1_line_fault_domib_eac.omib)
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
        assert cmath.isclose(first_point.time, 0.05449518005743059, abs_tol=10e-9)
        assert cmath.isclose(first_point.angle, rotor_angle.angle, abs_tol=10e-9)
        assert cmath.isclose(first_point.angular_speed, 0.006517454875201973, abs_tol=10e-9)
        assert first_point.network_state == NetworkState.DURING_FAULT
