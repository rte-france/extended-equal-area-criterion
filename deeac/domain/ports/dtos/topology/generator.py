# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from pydantic import BaseModel
from typing import Optional

from .bus import Bus
from deeac.domain.ports.dtos import Value


class Generator(BaseModel):
    """
    Generator in a topology.
    """
    name: str
    connected: bool
    bus: Bus
    active_power: Optional[Value]
    max_active_power: Value
    reactive_power: Optional[Value]
    direct_transient_reactance: Value
    inertia_constant: Value
    source: Optional[str]
    regulating: bool
