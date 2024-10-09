# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Optional
from .event import Event

from deeac.domain.ports.dtos import Value


class BusShortCircuitEvent(Event):
    """
    Short circuit on a bus.
    """
    bus_name: str
    fault_resistance: Optional[Value]
    fault_reactance: Optional[Value]