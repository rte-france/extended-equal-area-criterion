# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import numpy as np

from deeac.domain.models.matrices import ImpedanceMatrix


class TestImpedanceMatrix:

    def test_impedance_matrix(self, simple_network, simple_network_impedance_matrix, simple_network_admittance_matrix):
        impedance_matrix = ImpedanceMatrix(simple_network_admittance_matrix)
        assert impedance_matrix.dimension == simple_network_impedance_matrix.dimension
        np.testing.assert_array_almost_equal(
            impedance_matrix._matrix,
            simple_network_impedance_matrix._matrix,
            decimal=9
        )
        for bus in impedance_matrix._bus_indexes:
            assert impedance_matrix._bus_indexes[bus] == simple_network_impedance_matrix._bus_indexes[bus]
