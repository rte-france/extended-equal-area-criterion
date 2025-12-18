# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from pydantic import NonNegativeFloat, NonNegativeInt, PositiveFloat
from typing import List, Optional
from enum import Enum

from .network_data import NetworkData, OpeningCode


class TransformerRegulatingMode(Enum):
    NOT_REGULATING = "N"
    VOLTAGE = "V"
    ACTIVE_FLUX_SIDE_1 = "1"
    ACTIVE_FLUX_SIDE_2 = "2"


class TransformerTap(NetworkData):
    """
    Data of a transformer tap.
    """
    tap_number: int
    sending_side_voltage: NonNegativeFloat
    receiving_side_voltage: NonNegativeFloat
    leakage_impedance: float
    phase_shift_angle: float


class Transformer(NetworkData):
    """
    Data of a generic transformer in a network (must be specialized).
    """
    sending_node: str
    receiving_node: str
    opening_code: Optional[OpeningCode]
    parallel_index: str


class Type1Transformer(Transformer):
    """
    Data of a transformer with fixed real ratio (type 1).
    """
    resistance: float
    reactance: float
    rated_apparent_power: float
    transformation_ratio: PositiveFloat


class Type8Transformer(Transformer):
    """
    Data of a detailed transformer (type 8).
    """
    rated_apparent_power: float
    nominal_tap_number: NonNegativeInt
    initial_tap_position: NonNegativeInt
    regulated_node_name: Optional[str]
    min_active_flux: Optional[float]
    max_active_flux: Optional[float]
    regulating_mode: TransformerRegulatingMode
    voltage_target: Optional[NonNegativeFloat]
    taps: List[TransformerTap]
