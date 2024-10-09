# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import numpy as np
from deeac.domain.models.matrices import BusMatrix


class TestBusMatrix:

    def test_bus_matrix(self, simple_network):
        buses = simple_network.get_simplified_network()[0].buses
        bus_indexes = {
            buses[0].name: 0,
            buses[1].name: 1,
            buses[2].name: 2,
            buses[3].name: 3,
            buses[4].name: 4,
            buses[5].name: 5,
            buses[6].name: 6
        }
        array = np.array([
            [0, 1, 2, 3, 4, 5, 6],
            [10, 11, 12, 13, 14, 15, 16],
            [20, 21, 22, 23, 24, 25, 26],
            [30, 31, 32, 33, 34, 35, 36],
            [40, 41, 42, 43, 44, 45, 46],
            [50, 51, 52, 53, 54, 55, 56],
            [60, 61, 62, 63, 64, 65, 36]
        ])
        matrix = BusMatrix(array, bus_indexes)
        assert matrix.dimension == 7
        assert matrix._bus_indexes == bus_indexes
        assert np.array_equal(matrix._matrix, array)

        # Test get bus names
        buses = set(buses)
        assert matrix.bus_names == {bus.name for bus in buses}

    def test_get_item(self, simple_network):
        # Create a simple matrix to ease the test
        buses = simple_network.get_simplified_network()[0].buses
        bus_indexes = {
            buses[0].name: 0,
            buses[1].name: 1,
            buses[2].name: 2,
            buses[3].name: 3,
            buses[4].name: 4,
            buses[5].name: 5,
            buses[6].name: 6
        }
        matrix = BusMatrix(
            np.array([
                [0, 1, 2, 3, 4, 5, 6],
                [10, 11, 12, 13, 14, 15, 16],
                [20, 21, 22, 23, 24, 25, 26],
                [30, 31, 32, 33, 34, 35, 36],
                [40, 41, 42, 43, 44, 45, 46],
                [50, 51, 52, 53, 54, 55, 56],
                [60, 61, 62, 63, 64, 65, 36]
            ]),
            bus_indexes
        )

        for (i, bus_i) in enumerate(buses):
            for (j, bus_j) in enumerate(buses):
                assert matrix[buses[i].name, buses[j].name] == matrix._matrix[i, j]
