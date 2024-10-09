# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import cmath

from deeac.domain.models.rotor_angle_trajectory_calculator.taylor_series import OMIBTaylorSeries


class TestOMIBCalculator:

    def test_get_trajectory_times(self, case1_line_fault_zoomib_eac, case1_line_fault_domib_eac):
        # ZOOMIB
        series = OMIBTaylorSeries(case1_line_fault_zoomib_eac.omib)
        initial_angle = case1_line_fault_zoomib_eac.omib.initial_rotor_angle
        transition_angle = case1_line_fault_zoomib_eac.critical_clearing_angle
        last_angle = case1_line_fault_zoomib_eac.maximum_angle
        angles = [initial_angle, transition_angle, last_angle]
        times = series.get_trajectory_times(angles, transition_angle)
        assert cmath.isclose(times[0], 0, abs_tol=10e-9)
        assert cmath.isclose(times[1], 0.26732036492951583, abs_tol=10e-9)
        assert cmath.isclose(times[2], 0.5087925117043797, abs_tol=10e-9)
        # Add a time shift
        series = OMIBTaylorSeries(case1_line_fault_zoomib_eac.omib, transition_angle_shift=0.01)
        times = series.get_trajectory_times(angles, transition_angle)
        assert cmath.isclose(times[0], 0, abs_tol=10e-9)
        assert cmath.isclose(times[1], 0.26732036492951583, abs_tol=10e-9)
        # Only the maximum time should have changed
        assert cmath.isclose(times[2], 0.5052577853491889, abs_tol=10e-9)

        # DOMIB
        series = OMIBTaylorSeries(case1_line_fault_domib_eac.omib)
        initial_angle = case1_line_fault_domib_eac.omib.initial_rotor_angle
        transition_angle = case1_line_fault_domib_eac.critical_clearing_angle
        intermediate_angle = 1.9
        last_angle = case1_line_fault_domib_eac.maximum_angle
        angles = [initial_angle, transition_angle, intermediate_angle, last_angle]
        times = series.get_trajectory_times(angles, transition_angle)
        assert cmath.isclose(times[0], 0, abs_tol=10e-9)
        assert cmath.isclose(times[1], 0.26711185212860333, abs_tol=10e-9)
        assert cmath.isclose(times[2], 0.3832019913635765, abs_tol=10e-9)
        assert cmath.isclose(times[3], 1.2030764527582598, abs_tol=10e-9)
        # Add a time shift
        series = OMIBTaylorSeries(case1_line_fault_domib_eac.omib, transition_angle_shift=0.01)
        times = series.get_trajectory_times(angles, transition_angle)
        assert cmath.isclose(times[0], 0, abs_tol=10e-9)
        assert cmath.isclose(times[1], 0.26711185212860333, abs_tol=10e-9)
        # The two times after the transition time should have changed
        assert cmath.isclose(times[2], 0.3807617020152794, abs_tol=10e-9)
        assert cmath.isclose(times[3], 0.5522837591365115, abs_tol=10e-9)
