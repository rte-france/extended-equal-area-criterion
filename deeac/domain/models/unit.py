# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from enum import Enum
from numpy import pi

from deeac.domain.exceptions import UnitTypeException, UnitScaleException


class UnitType(Enum):
    """
    Type of unit.
    """
    APPARENT_POWER = "apparent_power"
    ACTIVE_POWER = "active_power"
    REACTIVE_POWER = "reactive_power"
    CURRENT = "current"
    VOLTAGE = "voltage"
    ANGLE = "angle"
    RESISTANCE = "resistance"
    CONDUCTANCE = "conductance"
    FREQUENCE = "frequence"
    PER_UNIT = "per_unit"
    SCALAR = "scalar"
    TIME = "time"


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
    MWS_PER_MVA = "MWs/MVA"
    DEG = "deg"
    RAD = "rad"
    HZ = "Hz"
    KHZ = "kHz"
    MHZ = "MHz"
    PU = "PU"
    SCALAR = "SCALAR"
    SEC = "s"
    MSEC = "ms"

    @property
    def type(self) -> UnitType:
        """
        Get the type of this unit.

        :return: Unit type.
        """
        return UNIT_TYPES[self]


"""
Allowed scales for each type of unit.
"""
UNIT_SCALES = {
    UnitType.APPARENT_POWER: {Unit.VA: 1, Unit.KVA: 1e3, Unit.MVA: 1e6},
    UnitType.ACTIVE_POWER: {Unit.W: 1, Unit.KW: 1e3, Unit.MW: 1e6},
    UnitType.REACTIVE_POWER: {Unit.VAR: 1, Unit.KVAR: 1e3, Unit.MVAR: 1e6},
    UnitType.VOLTAGE: {Unit.V: 1, Unit.KV: 1e3, Unit.MV: 1e6},
    UnitType.CURRENT: {Unit.A: 1},
    UnitType.RESISTANCE: {Unit.OHM: 1},
    UnitType.CONDUCTANCE: {Unit.S: 1},
    UnitType.ANGLE: {Unit.DEG: 1, Unit.RAD: 180 / pi},
    UnitType.FREQUENCE: {Unit.HZ: 1, Unit.KHZ: 1e3, Unit.MHZ: 1e6},
    UnitType.PER_UNIT: {Unit.PU: 1},
    UnitType.SCALAR: {Unit.SCALAR: 1},
    UnitType.TIME: {Unit.MSEC: 1e-3, Unit.SEC: 1}
}

"""
Units to their types.
"""

UNIT_TYPES = {}
for u_type, units in UNIT_SCALES.items():
    for u in units:
        UNIT_TYPES[u] = u_type

"""
Mapping of unit values to their Unit object (faster than using Unit(value) when called multiple times).
"""
UNIT_MAPPING = {}
for unit in Unit:
    UNIT_MAPPING[unit.value] = unit


def conversion_factor(from_unit: Unit, to_unit: Unit) -> float:
    """
    Get the conversion factor from a given unit to a another.
    The "from" value must be then mutliplied by the factor to get the "to" value.

    :param from_unit: Input unit.
    :param to_unit: Output unit.
    :return: Conversion factor.
    :raise UnitTypeException if the output unit is not of the same type a sthis unit.
    :raise UnitScaleException if the output unit does not have any associated scale.
    """
    if from_unit == to_unit:
        return 1.0

    # Check same unit type
    from_unit_type = from_unit.type
    if from_unit_type != to_unit.type:
        raise UnitTypeException(from_unit.name, to_unit.name)

    # Get the unit scale
    try:
        scale = UNIT_SCALES[from_unit_type]
    except KeyError:
        raise UnitScaleException(from_unit)

    # Return conversion factor
    return scale[from_unit] / scale[to_unit]
