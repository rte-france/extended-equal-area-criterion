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

from deeac.domain.models import Transformer
from deeac.domain.exceptions import DisconnectedElementException, TransformerImpedanceException


class TestTransformer:
    def test_repr(self, simple_tfo):
        assert repr(simple_tfo) == (
            "Transformer: R=[300 ohm [Base: 100 ohm]] X=[1000 ohm [Base: 100 ohm]] phase shift angle=[10 deg] "
            "Closed at primary=[True] Closed at secondary=[True]"
        )

    def test_impedance(self, simple_tfo):
        assert cmath.isclose(simple_tfo.impedance, 3 + 10j, abs_tol=10e-9)
        # Check if disconnected
        simple_tfo.closed_at_first_bus = False
        with pytest.raises(DisconnectedElementException):
            simple_tfo.impedance
        simple_tfo.closed_at_first_bus = True
        with pytest.raises(TransformerImpedanceException):
            Transformer().admittance

    def test_addmittance(self, simple_tfo):
        assert cmath.isclose(simple_tfo.admittance, 0.027522935779816512 - 0.09174311926605504j, abs_tol=10e-9)
        # Check if disconnected
        simple_tfo.closed_at_second_bus = False
        assert simple_tfo.admittance == 0j
        simple_tfo.closed_at_second_bus = True

    def test_shunt_admittance(self, simple_tfo):
        assert simple_tfo.shunt_admittance == (0.01-0.01j)

    def test_closed(self, simple_tfo):
        assert simple_tfo.closed
        simple_tfo.closed_at_second_bus = False
        assert not simple_tfo.closed
        simple_tfo.closed_at_first_bus = False
        assert not simple_tfo.closed
        simple_tfo.closed_at_second_bus = True
        assert not simple_tfo.closed
        simple_tfo.closed_at_first_bus = True
        assert simple_tfo.closed
