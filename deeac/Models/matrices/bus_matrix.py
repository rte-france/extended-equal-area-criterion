"""
Module for bus_matrix.

:module: bus_matrix
"""
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



class BusMatrix:
    """
    Busmatrix.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar matrix: matrix.
    :ivar bus_indexes: bus indexes.
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

    @property
    def bus_index_map(self) -> Dict[str, int]:
        """
        Bus index map.
        
        :return: Return value.
        :rtype: Dict[str, int]
        """
        return self._bus_indexes

    def __getitem__(self, buses: Tuple[str, str]) -> complex:
        """
        getitem  .
        
        :param buses: buses.
        """
        try:
            return self._matrix[self._bus_indexes[buses[0]], self._bus_indexes[buses[1]]]
        except KeyError:
            raise ValueError(*buses)

    def indices_for(self, bus_names: List[str]) -> List[int]:
        """
        Indices for.
        
        :param bus_names: bus names.
        """
        try:
            return [self._bus_indexes[name] for name in bus_names]
        except KeyError as exc:
            raise ValueError(str(exc)) from exc

    @staticmethod
    def _build_index_mapping(buses: Union[Deque, List]) -> Dict[str, int]:
        """
        Build the mapping of the buses to their index in the matrix.
        Their index is used to access the matrix. For example, element at (0, 0) in the matrix
        corresponds to the first bus (at index 0) in the list.
        
        :param buses: Ordered list of the buses represented by the matrix.
        """
        return {bus.name: i for (i, bus) in enumerate(buses)}
