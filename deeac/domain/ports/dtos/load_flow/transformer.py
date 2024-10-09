# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from pydantic import BaseModel, NonNegativeInt
from typing import List


class Transformer(BaseModel):
    """
    Load flow results for a transformer.
    """
    sending_bus: str
    receiving_bus: str
    parallel_id: str
    tap_number: NonNegativeInt


class TransformerNodeData(BaseModel):
    """
    Load flow results for a transformer node.
    """
    orig_node: str
    zone: str
    types: List[str]
    parallel_ids: List[str]
    nodes: List[float]
    resistances: List[float]
    reactances: List[float]
    shunt_susceptances: List[float]
    shunt_conductances: List[float]


class TransformerTapData(BaseModel):
    """
    Information on a transformer tap
    """
    sending_node: str
    receiving_node: str
    tap_numbers: List[int]
    phase_angles: List[float]
    sending_node_voltages: List[float]
    receiving_node_voltages: List[float]
