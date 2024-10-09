# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import cmath

import numpy as np
from typing import List, Dict, Deque, Any
from collections import deque
from scipy.sparse import linalg, csc_matrix
from deeac.domain.models import Bus, Generator, Transformer, Line
from .bus_matrix import BusMatrix


class AdmittanceMatrix(BusMatrix):
    """
    Class that represents an admittance matrix.
    The matrix is sorted so that all the buses connected to at least one generator are associated to the first indexes.
    """

    def __init__(self, buses: List[Bus]):
        """
        Initialize the matrix.

        :param buses: List of the buses represented by the matrix.
        """
        # Sort buses so that buses associated to a generator come first
        self._generator_buses = deque()
        sorted_buses = deque()
        for bus in buses:
            if len(bus.generators) > 0:
                self._generator_buses.appendleft(bus)
                sorted_buses.appendleft(bus)
            else:
                sorted_buses.append(bus)
        # Get indexes
        bus_indexes = self._build_index_mapping(sorted_buses)

        # Build the matrix
        matrix = self._build_matrix(sorted_buses, bus_indexes)
        self._reduced_matrix = None

        super().__init__(matrix=matrix, bus_indexes=bus_indexes)

    @property
    def generator_buses(self) -> Deque[Generator]:
        """
        Return a list of the buses associated to a generator.

        :return: A list of the buses associated to a generator.
        """
        return self._generator_buses

    @staticmethod
    def add_to_dict(dictionary: Dict, key: Any, value: Any):
        """
        Adds a new value to a dictionary or adds it to a pre-existing value
        """
        if key not in dictionary:
            dictionary[key] = value
        else:
            dictionary[key] += value

    def _build_matrix(self, buses: Deque[Bus], bus_indexes: Dict[str, int]) -> np.array:
        """
        Build the admittance matrix.

        :param buses: List of buses sorted so that buses connected to a generator appear first.
        :param bus_indexes: Index mapping of the buses to use to build the matrix.
        :return: A numpy array with the content of the admittance matrix.
        """
        sparse_data = dict()
        # Compute matrix
        dimension = len(bus_indexes)
        considered_branches = set()
        for i, bus in enumerate(buses):
            for load in bus.loads:
                # Diagonal element [y_i]: Add admittance of the loads connected to the bus
                self.add_to_dict(sparse_data, (i, i), load.admittance)

            for bank in bus.capacitor_banks:
                # Diagonal element [y_i]: Add admittance of the capacitor banks connected to the bus
                self.add_to_dict(sparse_data, (i, i), bank.admittance)

            for branch in bus.branches:
                if branch in considered_branches:
                    # Branch already considered
                    continue

                branch_admittance_j = 0
                branch_admittance_i = 0
                admittance_sum_i = 0
                admittance_sum_j = 0
                for element in branch.parallel_elements.values():
                    if isinstance(element, Transformer) is True:
                        impedance = element.impedance
                        shunt_admittance = element.shunt_admittance
                        if element.transformer_type == 8:
                            ratio = cmath.rect(element.ratio, np.deg2rad(element.phase_shift_angle))
                            sending_shunt_admittance = np.conj(ratio) * (ratio - 1) / impedance + ratio ** 2 * shunt_admittance
                            receiving_shunt_admittance = (1 - ratio) / impedance
                            admittance = element.admittance
                            if element.sending_node == bus.name:
                                branch_admittance_i += admittance * np.conj(ratio)
                                branch_admittance_j += admittance * ratio
                                admittance_sum_i += admittance * np.conj(ratio) + sending_shunt_admittance
                                admittance_sum_j += admittance * ratio + receiving_shunt_admittance
                            else:
                                branch_admittance_j += admittance * np.conj(ratio)
                                branch_admittance_i += admittance * ratio
                                admittance_sum_j += admittance * np.conj(ratio) + sending_shunt_admittance
                                admittance_sum_i += admittance * ratio + receiving_shunt_admittance

                        else:
                            ratio = element.ratio
                            admittance = element.admittance * ratio
                            branch_admittance_i += admittance
                            branch_admittance_j += admittance
                            sending_shunt_admittance = ratio * (ratio - 1) / impedance
                            receiving_shunt_admittance = (1 - ratio) / impedance + shunt_admittance
                            if element.sending_node == bus.name:
                                admittance_sum_i += admittance + sending_shunt_admittance
                                admittance_sum_j += admittance + receiving_shunt_admittance
                            else:
                                admittance_sum_j += admittance + sending_shunt_admittance
                                admittance_sum_i += admittance + receiving_shunt_admittance

                    elif isinstance(element, Line) is True:
                        admittance_with_shunt = element.admittance + element.shunt_admittance / 2
                        branch_admittance_j += element.admittance
                        branch_admittance_i += element.admittance
                        admittance_sum_i += admittance_with_shunt
                        admittance_sum_j += admittance_with_shunt
                    else:
                        raise ValueError(f"Unknown element type {type(element)}")

                # Diagonal element [sum(y_ik) with k != i]: Add admittance and shunt-admittance of connected branches
                considered_branches.add(branch)

                # Get connected bus and its index
                connected_bus = branch.first_bus if branch.first_bus != bus else branch.second_bus
                j = bus_indexes[connected_bus.name]

                self.add_to_dict(sparse_data, (i, i), admittance_sum_i)
                self.add_to_dict(sparse_data, (j, j), admittance_sum_j)

                self.add_to_dict(sparse_data, (i, j), - branch_admittance_i)
                self.add_to_dict(sparse_data, (j, i), - branch_admittance_j)

        rows = [index[0] for index in sparse_data.keys()]
        columns = [index[1] for index in sparse_data.keys()]
        return csc_matrix((list(sparse_data.values()), (rows, columns)), shape=(dimension, dimension), dtype=complex)

    @property
    def reduction(self) -> 'ReducedAdmittanceMatrix':
        """
        Return a reduced version of the matrix.
        The reduction allows to eliminate all the nodes except the synchronous generators and other source buses (HVDC,
        windfarms, ...).

        :return: The reduced admittance matrix.
        """
        if self._reduced_matrix is not None:
            # Matrix already computed
            return self._reduced_matrix
        self._reduced_matrix = ReducedAdmittanceMatrix(self)
        return self._reduced_matrix


class ReducedAdmittanceMatrix(BusMatrix):
    """
    Class that represents an admittance matrix reduced on the generators.
    """

    def __init__(self, admittance_matrix: AdmittanceMatrix):
        """
        Initialize the matrix.

        :param admittance_matrix: Admittance matrix to use to compute the reduction.
        """
        matrix = self._build_matrix(admittance_matrix)
        # Get indexes and create the bus matrix
        bus_indexes = self._build_index_mapping(admittance_matrix.generator_buses)
        super().__init__(matrix=matrix, bus_indexes=bus_indexes)

    @staticmethod
    def _build_matrix(admittance_matrix: AdmittanceMatrix) -> np.array:
        """
        Build the reduced admittance matrix.

        This method considers that the admittance matrix Y can be split into the following 4 parts:
            [Y_generators Y_upper_right   ]
            [Y_lower_left Y_non_generators]
        In this representation:
            - Y_generators is the part of Y for all the buses connected to at least 1 generator
            - Y_non_generators is the part of Y for all the buses not connected to any generator

        :param admittance_matrix: Admittance matrix used for the reduction.
        :return: A numpy array with the content of the reduced admittance matrix.
        """
        # Number of buses in the matrix connected to a generator
        nb_generator_buses = len(admittance_matrix.generator_buses)

        # Split the matrix into 4 parts
        y_generators = admittance_matrix.matrix[:nb_generator_buses, :nb_generator_buses]
        y_non_generators = admittance_matrix.matrix[nb_generator_buses:, nb_generator_buses:]
        y_upper_right = admittance_matrix.matrix[:nb_generator_buses, nb_generator_buses:]
        y_lower_left = admittance_matrix.matrix[nb_generator_buses:, :nb_generator_buses]

        # Compute the inverse of matrix with buses not associated to generators using LU decomposition for performances
        lu = linalg.splu(y_non_generators)
        eye_matrix = np.eye(y_non_generators.shape[0])
        y_non_generators_inv = lu.solve(eye_matrix)

        # Compute the reduced matrix
        reduced_matrix = y_generators - (y_upper_right @ y_non_generators_inv @ y_lower_left)

        return reduced_matrix
