"""
Module for admittance_matrix.

:module: admittance_matrix
"""
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
from typing import List, Dict, Iterable
from scipy.sparse import linalg, coo_matrix
from deeac.Models.bus import Bus
from deeac.Models.transformer import Transformer
from deeac.Models.line import Line
from deeac.Models.matrices.bus_matrix import BusMatrix


def _bus_without_generators_sort_key(bus: Bus) -> int:
    """
    Sort generator buses before passive buses.
    
    :param bus: Bus to rank.
    :return: ``0`` when the bus hosts generators, ``1`` otherwise.
    """
    return int(len(bus.generators) == 0)


class AdmittanceMatrix(BusMatrix):
    """
    Admittancematrix.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar buses: buses.
    """

    def __init__(self, buses: List[Bus]):
        """
        Initialize the matrix.
        
        :param buses: List of the buses represented by the matrix.
        """
        # Sort buses so that buses associated to a generator come first
        sorted_buses: List[Bus] = sorted(buses, key=_bus_without_generators_sort_key)
        self._generator_buses = [bus for bus in sorted_buses if bus.generators]

        # Get indexes
        bus_indexes = self._build_index_mapping(sorted_buses)

        # Build the matrix
        matrix = self._build_matrix(sorted_buses, bus_indexes)
        self._reduced_matrix = None

        super().__init__(matrix=matrix, bus_indexes=bus_indexes)

    @property
    def generator_buses(self) -> List[Bus]:
        """
        Return a list of the buses associated to a generator.
        
        :return: A list of the buses associated to a generator.
        """
        return self._generator_buses

    def _build_matrix(self, buses: Iterable[Bus], bus_indexes: Dict[str, int]) -> np.ndarray:
        """
        Build the admittance matrix.
        
        :param buses: List of buses sorted so that buses connected to a generator appear first.
        :param bus_indexes: Index mapping of the buses to use to build the matrix.
        :return: A numpy sparse matrix (csc) with the content of the admittance matrix.
        """
        data = []
        rows = []
        cols = []
        dimension = len(bus_indexes)
        considered_branches = set()

        for i, bus in enumerate(buses):
            loads = bus.loads
            capacitor_banks = bus.capacitor_banks
            bus_name = bus.name

            for load in loads:
                rows.append(i)
                cols.append(i)
                data.append(load.admittance)

            for bank in capacitor_banks:
                rows.append(i)
                cols.append(i)
                data.append(bank.admittance)

            for branch in bus.branches:
                if branch in considered_branches:
                    continue

                branch_admittance_j = 0
                branch_admittance_i = 0
                admittance_sum_i = 0
                admittance_sum_j = 0

                for element in branch.parallel_elements.values():
                    if isinstance(element, Transformer):
                        impedance = element.impedance
                        shunt_admittance = element.shunt_admittance

                        if element.transformer_type == 8:
                            ratio = cmath.rect(element.ratio, element.phase_shift_angle)
                            ratio_conj = np.conj(ratio)
                            ratio_squared = ratio * ratio
                            sending_shunt_admittance = ratio_conj * (
                                ratio - 1) / impedance + ratio_squared * shunt_admittance
                            receiving_shunt_admittance = (1 - ratio) / impedance
                            admittance = element.admittance

                            if element.sending_node == bus_name:
                                branch_admittance_i += admittance * ratio_conj
                                branch_admittance_j += admittance * ratio
                                admittance_sum_i += admittance * ratio_conj + sending_shunt_admittance
                                admittance_sum_j += admittance * ratio + receiving_shunt_admittance
                            else:
                                branch_admittance_j += admittance * ratio_conj
                                branch_admittance_i += admittance * ratio
                                admittance_sum_j += admittance * ratio_conj + sending_shunt_admittance
                                admittance_sum_i += admittance * ratio + receiving_shunt_admittance
                        else:
                            ratio = element.ratio
                            admittance = element.admittance * ratio
                            branch_admittance_i += admittance
                            branch_admittance_j += admittance
                            sending_shunt_admittance = ratio * (ratio - 1) / impedance
                            receiving_shunt_admittance = (1 - ratio) / impedance + shunt_admittance

                            if element.sending_node == bus_name:
                                admittance_sum_i += admittance + sending_shunt_admittance
                                admittance_sum_j += admittance + receiving_shunt_admittance
                            else:
                                admittance_sum_j += admittance + sending_shunt_admittance
                                admittance_sum_i += admittance + receiving_shunt_admittance

                    elif isinstance(element, Line):
                        admittance_with_shunt = element.admittance_pu + element.shunt_admittance_pu / 2
                        branch_admittance_i += element.admittance_pu
                        branch_admittance_j += element.admittance_pu
                        admittance_sum_i += admittance_with_shunt
                        admittance_sum_j += admittance_with_shunt
                    else:
                        raise ValueError(f"Unknown element type {type(element)}")

                considered_branches.add(branch)

                first_bus = branch.first_bus
                second_bus = branch.second_bus
                connected_bus = first_bus if first_bus != bus else second_bus
                j = bus_indexes[connected_bus.name]

                rows.extend([i, j])
                cols.extend([i, j])
                data.extend([admittance_sum_i, admittance_sum_j])

                rows.extend([i, j])
                cols.extend([j, i])
                data.extend([-branch_admittance_i, -branch_admittance_j])

        # Build the sparse matrix using COO format, then convert to CSC
        return coo_matrix((data, (rows, cols)), shape=(dimension, dimension), dtype=complex).tocsc()

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
    Reducedadmittancematrix.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar admittance_matrix: admittance matrix.
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
    def _build_matrix(admittance_matrix: AdmittanceMatrix) -> np.ndarray:
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

        # Compute the reduced matrix
        lu = linalg.splu(y_non_generators)
        temp = lu.solve(y_lower_left.toarray())
        reduced_matrix = y_generators - y_upper_right @ temp

        return reduced_matrix
