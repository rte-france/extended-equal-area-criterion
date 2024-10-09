# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from numpy import array
from typing import Dict, Set, Tuple, Deque, List, Union

from deeac.domain.exceptions import BusMatrixException


class BusMatrix:
    """
    Class that represents a bus matrix with useful functions.
    """

    def __init__(self, matrix: array, bus_indexes: Dict[str, int]):
        """
        Initialize the matrix.

        :param matrix: Content of the matrix as a numpy array.
        :param bus_indexes: Mapping of the names of the buses represented by the matrix to their index.
                            The indexes are used to access the matrix. For example, element at (0, 0) in the matrix
                            corresponds to the bus at index 0 in the dictionary.
        """
        self.dimension = len(bus_indexes)
        self._matrix = matrix
        self._bus_indexes = bus_indexes

    @property
    def bus_names(self) -> Set[str]:
        """
        Set of the names of the buses represented by this matrix.

        :return: The set of bus names.
        """
        return set(self._bus_indexes.keys())

    @property
    def matrix(self) -> array:
        """
        Return the array containing the values of the matrix.

        :return: A numpy array corresponding to the matrix values.
        """
        return self._matrix

    def __getitem__(self, buses: Tuple[str, str]) -> complex:
        """
        Define accessor for the matrix based on two bus names.

        param buses: A tuple of bus names used to access an element of the matrix.
        return: The value in the matrix corresponding to the two busses with the specified names.
        raises: BusMatrixException if no value can be found for the couple of buses.
        """
        try:
            return self._matrix[self._bus_indexes[buses[0]], self._bus_indexes[buses[1]]]
        except KeyError:
            raise BusMatrixException(*buses)

    @staticmethod
    def _build_index_mapping(buses: Union[Deque, List]) -> Dict[str, int]:
        """
        Build the mapping of the buses to their index in the matrix.
        Their index is used to access the matrix. For example, element at (0, 0) in the matrix
        corresponds to the first bus (at index 0) in the list.

        :param buses: Ordered list of the buses represented by the matrix.
        """
        return {bus.name: i for (i, bus) in enumerate(buses)}
