# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import numpy as np
from deeac.domain.models.matrices import AdmittanceMatrix


class TestAdmittanceMatrix:

    def test_sorted_matrix(self, simple_network, simple_network_admittance_matrix):
        # Get buses:
        # GENBUS SLACKBUS BUS1_BUS2 BUS3 INTERNAL_VOLTAGE_GEN1 INTERNAL_VOLTAGE_GEN2 INTERNAL_VOLTAGE_SLACKGEN
        buses = simple_network.get_simplified_network()[0].buses
        # Randomize buses to test the sorting:
        # BUS1_BUS2 INTERNAL_VOLTAGE_GEN1 SLACKBUS INTERNAL_VOLTAGE_GEN2 INTERNAL_VOLTAGE_SLACKGEN BUS3 GENBUS
        buses = [buses[2], buses[4], buses[1], buses[5], buses[6], buses[3], buses[0]]
        matrix = AdmittanceMatrix(buses)
        np.testing.assert_array_almost_equal(
            matrix._matrix.toarray(),
            simple_network_admittance_matrix._matrix,
            decimal=9
        )
        # Sorted buses:
        # INTERNAL_VOLTAGE_SLACKGEN INTERNAL_VOLTAGE_GEN2 INTERNAL_VOLTAGE_GEN1 BUS1_BUS2 SLACKBUS BUS3 GENBUS
        assert matrix.dimension == len(buses)
        assert list(matrix._generator_buses) == [buses[4], buses[3], buses[1]]

        # Check if get_item works properly on sorted buses
        buses = [buses[4], buses[3], buses[1], buses[0], buses[2], buses[5], buses[6]]
        assert len(buses) == len(matrix._bus_indexes)
        for (i, bus_i) in enumerate(buses):
            assert matrix._bus_indexes[bus_i.name] == i
            for (j, bus_j) in enumerate(buses):
                assert matrix[buses[i].name, buses[j].name] == matrix._matrix[i, j]

    def test_reduction(self, simple_network, simple_network_reduced_admittance_matrix):
        matrix = simple_network.get_simplified_network()[0].admittance_matrix
        reduced_matrix = matrix.reduction
        assert reduced_matrix.dimension == 3
        np.testing.assert_array_almost_equal(
            reduced_matrix._matrix,
            simple_network_reduced_admittance_matrix._matrix,
            decimal=8
        )
        assert reduced_matrix._bus_indexes == simple_network_reduced_admittance_matrix._bus_indexes
