# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from pydantic import BaseModel, NonNegativeInt

from deeac.domain.ports.dtos import Value


class Transformer8(BaseModel):
    """
    Transformer type 8 in a topology
    """
    closed_at_sending_bus: bool
    closed_at_receiving_bus: bool
    sending_node: str
    receiving_node: str
    base_impedance: Value
    primary_base_voltage: Value
    secondary_base_voltage: Value
    initial_tap_number: NonNegativeInt
    phase_shift_angle: Value


class Transformer1(BaseModel):
    """
    Transformer type 1 in a topology
    """
    closed_at_sending_bus: bool
    closed_at_receiving_bus: bool
    sending_node: str
    receiving_node: str
    base_impedance: Value
    ratio: float
