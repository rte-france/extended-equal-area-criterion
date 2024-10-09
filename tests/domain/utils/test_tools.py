# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest
import numpy as np

from deeac.domain.exceptions import ElementNotFoundException
from deeac.domain.models import Value, PUBase, Unit
from deeac.domain.utils import get_element, deepcopy, inverse_sparse_matrix


class TestTools:

    def test_get_element(self):
        elements = {
            "element1": 1,
            "element2": 2
        }
        # Success
        assert get_element("element1", elements, int.__name__) == 1
        # Miss
        with pytest.raises(ElementNotFoundException) as e:
            get_element("element3", elements, int.__name__)
        assert isinstance(e.value, ElementNotFoundException)
        assert e.value.name == "element3"
        assert e.value.element_type == "int"

    def test_deepcopy(self):
        value = Value(4, Unit.KV, PUBase(10, Unit.V))
        copied_value = deepcopy(value)
        assert id(value) != id(copied_value)
        assert id(value.base) != id(copied_value.base)
        assert copied_value == Value(4, Unit.KV, PUBase(10, Unit.V))

    def test_inverse_matrix(self):
        matrix = np.array([[1, 0, 3], [0, 0, 1], [0, 8, 0]])
        np.testing.assert_array_almost_equal(
            inverse_sparse_matrix(matrix),
            np.linalg.inv(matrix),
            decimal=9
        )
