# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from pydantic import NonNegativeFloat
from enum import Enum
from typing import Optional

from .network_data import NetworkData, State


class GeneratorRegulatingMode(Enum):
    REGULATING = "V"
    NOT_REGULATING = "N"


class GeneratorStaticPart(NetworkData):
    """
    Static data of a generator in a network.
    """
    name: str
    state: State
    bus_name: str
    active_power: Optional[float]
    max_active_power: float
    reactive_power: Optional[float]
    target_voltage: Optional[NonNegativeFloat]
    regulating_mode: GeneratorRegulatingMode
    source: Optional[str]


class GeneratorDynamicPart(NetworkData):
    """
    Dynamic data of a generator in a network.
    """
    name: str
    rated_apparent_power: float
    base_voltage_machine_side: NonNegativeFloat
    direct_transient_reactance: float
    inertia_constant: NonNegativeFloat
