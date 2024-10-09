# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Optional
from enum import Enum

from .event_data import EventData


class BreakerPosition(Enum):
    """
    Position of the breaker on a branch.
    """
    SENDING_NODE = 'S'
    RECEIVING_NODE = 'R'


class BranchType(Enum):
    """
    Type of the branch containing the breaker
    """
    THREE_WINDING_TRANSFORMER = '1'
    COUPLING_DEVICE = '2'


class BreakerEvent(EventData):
    """
    Data of breaker event.
    """
    time: float
    sending_node: Optional[str]
    receiving_node: Optional[str]
    parallel_index: Optional[str]
    position: Optional[BreakerPosition]
    branch_type: Optional[BranchType]
    first_coupled_node: Optional[str]
    second_coupled_node: Optional[str]
    coupling_index: Optional[str]


class BreakerOpeningEvent(BreakerEvent):
    """
    Data of breaker opening event.
    """
    pass


class BreakerClosingEvent(BreakerEvent):
    """
    Data of breaker closing event.
    """
    pass
