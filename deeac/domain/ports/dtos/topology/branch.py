# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from pydantic import BaseModel
from typing import Dict, Union

from .bus import Bus
from .transformers import Transformer8, Transformer1
from .line import Line
from .breaker import Breaker


class Branch(BaseModel):
    """
    Branch linking two buses in a topology.
    """
    sending_bus: Bus
    receiving_bus: Bus
    parallel_elements: Dict[str, Union[Line, Breaker, Transformer1, Transformer8]] = {}