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

from .network_data import NetworkData


class HVDCConverterState(Enum):
    OFF = "S"


class HVDCCurrentSourceConverter(NetworkData):
    """
    Data of high voltage direct current (HVDC) current source converter (CSC) in a network.
    """
    name: str
    state: Optional[HVDCConverterState]
    bus_name: str


class HVDCVoltageSourceConverter(NetworkData):
    """
    Data of high voltage direct current (HVDC) voltage source converter (VSC) in a network.
    """
    name: str
    state: Optional[HVDCConverterState]
    bus_name: str
