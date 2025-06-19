# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import sys
import pickle
from numpy import array
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import splu
from typing import Dict, Any

from deeac.domain.exceptions import ElementNotFoundException

"""
Set of utility functions.
"""

sys.setrecursionlimit(50000)


def get_element(name: str, elements: Dict[str, Any], element_type: str) -> Any:
    """
    Get an element from a dictionary of elements based on its name.
    The dictionary keys must be the element names.

    :param name: The name of the element to find.
    :param elements: The dictionary of elements.
    :param element_type: Type of element to find in the dictionary
    :return: The element whose name if the one specified as argument.
    :raise: ElementNameException if the element is not in the dictionary.
    """
    try:
        return elements[name]
    except KeyError as e:
        raise ElementNotFoundException(e.args[0], element_type)


def deepcopy(object: Any) -> Any:
    """
    Copy an object using pickles for improved performances compared to deepcopy.

    :param object: The object to copy.
    :return: A copy of the object
    """
    return pickle.loads(pickle.dumps(object, protocol=-1))


def inverse_sparse_matrix(matrix: array) -> array:
    """
    Inverse a sparse matrix.

    :param matrix: The matrix to inverse.
    :return: The inverse of the input matrix.
    """
    sparse_matrix = csc_matrix(matrix)
    lu = splu(sparse_matrix)
    return lu.solve(csc_matrix.eye(matrix.shape[0]))
