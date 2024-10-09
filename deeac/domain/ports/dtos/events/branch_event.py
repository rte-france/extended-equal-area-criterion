# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from enum import Enum

from .event import Event


class BreakerPosition(Enum):
    """
    Position of the breaker on the branch that is targeted by this event.
    """
    FIRST_BUS = "FIRST_BUS"
    SECOND_BUS = "SECOND_BUS"


class BranchEvent(Event):
    """
    Event related to the opening or closing of a branch (Line or Transformer).
    """
    first_bus_name: str
    second_bus_name: str
    parallel_id: str
    breaker_position: BreakerPosition
    breaker_closed: bool
