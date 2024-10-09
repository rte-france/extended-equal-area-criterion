# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from abc import ABC
from pydantic import BaseModel
from enum import Enum


class OpeningCode(Enum):
    BOTH_SIDE_OPEN = "-"
    RECEIVING_SIDE_OPEN = "<"
    SENDING_SIDE_OPEN = ">"


class State(Enum):
    CONNECTED = "Y"
    NOT_CONNECTED = "N"


class NetworkData(BaseModel, ABC):
    """
    Basic network data.
    """
    pass
