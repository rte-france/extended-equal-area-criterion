# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from enum import Enum
from pydantic import BaseModel


class Unit(Enum):
    """
    Unit.
    """
    A = "A"
    W = "W"
    KW = "kW"
    MW = "MW"
    V = "V"
    KV = "kV"
    MV = "MV"
    VA = "VA"
    KVA = "kVA"
    MVA = "MVA"
    VAR = "VAr"
    KVAR = "kVAr"
    MVAR = "MVAr"
    OHM = "ohm"
    S = "S"
    DEG = "deg"
    RAD = "rad"
    PERCENT = "PERCENT"
    MWS_PER_MVA = "MWs/MVA"
    SCALAR = "SCALAR"


class Value(BaseModel):
    """
    Value with a unit.
    """
    value: float
    unit: Unit
