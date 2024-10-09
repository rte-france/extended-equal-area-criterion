# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from .bus_matrix import BusMatrix
from .admittance_matrix import AdmittanceMatrix
from deeac.domain.utils import inverse_sparse_matrix


class ImpedanceMatrix(BusMatrix):
    """
    Class that represents an impedance matrix.
    """

    def __init__(self, admittance_matrix: AdmittanceMatrix):
        """
        Initialize the matrix.

        :param admittance_matrix: Admittance matrix corresponding to this impedance matrix.
        """
        # Compute the impedance matrix
        matrix = inverse_sparse_matrix(admittance_matrix._matrix)
        super().__init__(matrix=matrix, bus_indexes=admittance_matrix._bus_indexes)
