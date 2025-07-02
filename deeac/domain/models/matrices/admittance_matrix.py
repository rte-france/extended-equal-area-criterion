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
from typing import List, Dict
from scipy.sparse import linalg, coo_matrix
from deeac.domain.models import Bus, Transformer, Line
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
        # Sort buses so that buses associated to a generator come first, then ren, then others
        sorted_buses = sorted(buses, key=lambda bus: 0 if len(bus.generators) > 0 else 1 if len(bus.ren) > 0 else 2)
        self._generator_buses = [bus for bus in sorted_buses if bus.generators]
        self._ren_buses = [bus for bus in sorted_buses if bus.ren and not bus.generators]

        # Get indexes
        bus_indexes = self._build_index_mapping(sorted_buses)

        # Build the matrix
        matrix = self._build_matrix(sorted_buses, bus_indexes)
        self._reduced_matrix = None

        super().__init__(matrix=matrix, bus_indexes=bus_indexes)

    @property
    def ren_buses(self) -> List[Bus]:
        """
        Return a list of the buses associated to a ren.

        :return: A list of the buses associated to a ren.
        """
        return self._ren_buses

    @property
    def generator_buses(self) -> List[Bus]:
        """
        Return a list of the buses associated to a generator.

        :return: A list of the buses associated to a generator.
        """
        return self._generator_buses

    @staticmethod
    def _build_matrix(buses: List[Bus], bus_indexes: Dict[str, int]) -> np.array:
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
        wind farms, ...).

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
        bus_indexes = self._build_index_mapping(admittance_matrix.generator_buses + admittance_matrix.ren_buses)
        super().__init__(matrix=matrix, bus_indexes=bus_indexes)

    @staticmethod
    def _build_matrix(admittance_matrix: AdmittanceMatrix) -> np.array:
        """
        Build the reduced admittance matrix.

        This method considers that the admittance matrix Y can be split into the following 9 parts:
            [Ynn Yns Ynr]
            [Ysn Yss Ysr]
            [Yrn Yrs Yrr]
        In this representation:
            - n is the index for all buses connected to at least 1 generator
            - s is the index for all buses not connected to any generator but connected to at least 1 ren
            - r is the index for all buses not connected to any generator or ren

        :param admittance_matrix: Admittance matrix used for the reduction.
        :return: A numpy array with the content of the reduced admittance matrix.
        """
        # Number of buses in the matrix connected to a generator or a ren
        nb_gen = len(admittance_matrix.generator_buses)
        nb_ren = len(admittance_matrix.ren_buses)

        # Split the matrix into 9 parts (n generators, s ren, r others)
        Ynn = admittance_matrix.matrix[:nb_gen, :nb_gen]
        Yns = admittance_matrix.matrix[:nb_gen, nb_gen:(nb_ren+nb_gen)]
        Ynr = admittance_matrix.matrix[:nb_gen, (nb_ren+nb_gen):]
        Ysn = admittance_matrix.matrix[nb_gen:(nb_gen+nb_ren), :nb_gen]
        Yss = admittance_matrix.matrix[nb_gen:(nb_gen+nb_ren), nb_gen:(nb_ren+nb_gen)]
        Ysr = admittance_matrix.matrix[nb_gen:(nb_gen+nb_ren), (nb_ren+nb_gen):]
        Yrn = admittance_matrix.matrix[(nb_gen+nb_ren):, :nb_gen]
        Yrs = admittance_matrix.matrix[(nb_gen+nb_ren):, nb_gen:(nb_ren+nb_gen)]
        Yrr = admittance_matrix.matrix[(nb_gen+nb_ren):, (nb_ren+nb_gen):]

        # LU Factorisation
        lu = linalg.splu(Yrr)

        # Schur products
        Yrr_inv_Yrn = lu.solve(Yrn.toarray())
        Yrr_inv_Yrs = lu.solve(Yrs.toarray())

        # Blocs calculation
        Rnn = Ynn - Ynr @ Yrr_inv_Yrn
        Rns = Yns - Ynr @ Yrr_inv_Yrs
        Rsn = Ysn - Ysr @ Yrr_inv_Yrn
        Rss = Yss - Ysr @ Yrr_inv_Yrs

        return np.block([[Rnn, Rns], [Rsn, Rss]])
