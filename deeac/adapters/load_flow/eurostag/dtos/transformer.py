# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from enum import Enum
from typing import Optional

from .load_flow_data import LoadFlowData


class TransformerType(Enum):
    FIXED_REAL_RATIO = "1"
    ADJUSTABLE_REAL_RATIO = "2"
    DETAILED = "8"
    QUADRATURE_PHASE = "9"
    FORTESCUE_GENERAL = "145"
    FORTESCUE_DETAILED = "147"
    IGNORE_0 = "0"
    IGNORE_6 = "6"


class Transformer(LoadFlowData):
    """
    Information on a transformer.
    """
    sending_node: str
    receiving_node: str
    parallel_index: str
    type: TransformerType


class TransformerNodeData(LoadFlowData):
    """
    Information on a transformer node
    """
    orig_node: Optional[str]
    orig_zone: Optional[str]
    node: Optional[str]
    zone: Optional[str]
    parallel_index: Optional[str]
    resistance: Optional[str]
    reactance: Optional[str]
    shunt_susceptance: Optional[str]
    shunt_conductance: Optional[str]
    type: Optional[TransformerType]


class TransformerTapData(LoadFlowData):
    """
    Information on a transformer tap
    """
    sending_node: Optional[str]
    receiving_node: Optional[str]
    parallel_index: Optional[str]
    tap_number: Optional[int]
    phase_angle: Optional[float]
    sending_node_voltage: Optional[float]
    receiving_node_voltage: Optional[float]
