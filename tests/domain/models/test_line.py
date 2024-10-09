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

from deeac.domain.exceptions import DisconnectedElementException


class TestLine:

    def test_repr(self, simple_line):
        assert repr(simple_line) == (
            "Line: R=[300 ohm [Base: 100 ohm]] X=[1000 ohm [Base: 100 ohm]] Gs=[40 S [Base: 10 S]] "
            "Bs=[20 S [Base: 10 S]] Closed at first bus=[True] Closed at second bus=[True] Metal short circuit=[False]"
        )

    def test_impedance(self, simple_line):
        assert cmath.isclose(simple_line.impedance, 3 + 10j, abs_tol=10e-9)
        # Check if disconnected
        simple_line.closed_at_first_bus = False
        with pytest.raises(DisconnectedElementException):
            simple_line.impedance
        simple_line.closed_at_first_bus = True

    def test_admittance(self, simple_line):
        assert cmath.isclose(simple_line.admittance, 0.027522935779816512 - 0.09174311926605504j, abs_tol=10e-9)
        # Check if disconnected
        simple_line.closed_at_first_bus = False
        assert simple_line.admittance == 0j
        simple_line.closed_at_first_bus = True

    def test_shunt_admittance(self, simple_line):
        assert cmath.isclose(simple_line.shunt_admittance, 4 + 2j, abs_tol=10e-9)
        # Check if disconnected
        simple_line.closed_at_first_bus = False
        assert simple_line.shunt_admittance == 0j
        simple_line.closed_at_first_bus = True

    def test_closed(self, simple_line):
        assert simple_line.closed
        simple_line.closed_at_second_bus = False
        assert not simple_line.closed
        simple_line.closed_at_first_bus = False
        assert not simple_line.closed
        simple_line.closed_at_second_bus = True
        assert not simple_line.closed
        simple_line.closed_at_first_bus = True
        assert simple_line.closed
