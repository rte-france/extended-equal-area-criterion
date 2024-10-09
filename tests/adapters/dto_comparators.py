# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import math
from pydantic import BaseModel
from typing import Any


def dtos_are_equal(dto1: Any, dto2: Any) -> bool:
    """
    Compare two DTOs.
    A DTO may be a pydantic BaseModel, a python primitive type, a list or a dict.
    Other objects are not supported.
    This comparator tries first the equal comparator, and a more complex comparison in case of failure.
    Floats are compared with a precision of 10e-9.

    :param dto1: First DTO to compare.
    :param dto2: Second DTO to compare.
    :return: True if the DTOs are equal, False otherwise.
    """
    if dto1 == dto2:
        # Try first equals operator
        return True

    # Equal operator does not work, go deeper
    if type(dto1) != type(dto2):
        # Types must be identical
        return False

    if isinstance(dto1, float):
        # Compare floats with a specified precision
        return math.isclose(dto1, dto2, abs_tol=10e-9)
    if isinstance(dto1, dict):
        # DTO is a dict
        for (key, element) in dto1.items():
            # Keys must be identical, as well as the values
            if key not in dto2 or not dtos_are_equal(element, dto2[key]):
                return False
        return True
    if isinstance(dto1, list):
        # DTO is a list
        if len(dto1) != len(dto2):
            # Lengths must be identical
            return False
        for (i, element) in enumerate(dto1):
            # Compare each element
            if not dtos_are_equal(element, dto2[i]):
                return False
        return True
    if isinstance(dto1, BaseModel):
        # Object is complex, compare fields
        fields = [field for field in dto1.__fields__]
        for field in fields:
            attr1 = getattr(dto1, field)
            attr2 = getattr(dto2, field)
            if not dtos_are_equal(attr1, attr2):
                return False
        return True

    return False
