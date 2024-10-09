# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from pydantic import NonNegativeFloat
from typing import Optional

from .network_data import NetworkData, OpeningCode


class Line(NetworkData):
    """
    Data if a line in a network.
    """
    sending_node: str
    receiving_node: str
    opening_code: Optional[OpeningCode]
    parallel_index: str
    resistance: NonNegativeFloat
    reactance: float
    semi_shunt_conductance: float
    semi_shunt_susceptance: float
    rated_apparent_power: float
