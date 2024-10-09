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

from .load_flow_data import LoadFlowData


class Result(LoadFlowData):
    """
    Result of a load flow.
    """
    area: Optional[str]
    node_name: Optional[str]
    voltage: Optional[NonNegativeFloat]
    phase_angle: Optional[float]
    production_active_power: Optional[float]
    production_reactive_power: Optional[float]
    load_active_power: Optional[float]
    load_reactive_power: Optional[float]
    connected_node_name: Optional[str]
    branch_parallel_index: Optional[str]
    transformer_tap: Optional[NonNegativeFloat]
