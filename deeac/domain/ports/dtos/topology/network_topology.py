# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from pydantic import BaseModel
from typing import List

from .bus import Bus, SlackBus
from .branch import Branch
from .ren import REN
from .generator import Generator
from .load import Load
from .capacitor_bank import CapacitorBank
from .static_var_compensator import StaticVarCompensator
from .high_voltage_direct_current import HVDCConverter
from deeac.domain.ports.dtos import Value


class NetworkTopology(BaseModel):
    """
    Network topology.
    """
    base_power: Value
    buses: List[Bus]
    slack_buses: List[SlackBus]
    branches: List[Branch]
    loads: List[Load]
    generators: List[Generator]
    ren: List[REN]
    capacitor_banks: List[CapacitorBank]
    static_var_compensators: List[StaticVarCompensator]
    hvdc_converters: List[HVDCConverter]
