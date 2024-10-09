# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Dict, Tuple
from pydantic import BaseModel

from .bus import Bus
from .load import Load
from .generator import Generator
from .transformer import Transformer, TransformerNodeData, TransformerTapData
from .hvdc_converter import HVDCConverter
from .static_var_compensator import StaticVarCompensator


class LoadFlowResults(BaseModel):
    """
    Results of a load flow.
    Buses, SVCs, HVDC converters, and generators are indexed by their names.
    Transformers are indexed by a tuple where the first element is the sending node, the second is the receiving node,
    and the last is the parallel index.
    """
    buses: Dict[str, Bus]
    loads: Dict[str, Load]
    generators: Dict[str, Generator]
    transformers: Dict[Tuple[str, str, str], Transformer]
    static_var_compensators: Dict[str, StaticVarCompensator]
    hvdc_converters: Dict[str, HVDCConverter]
    transformer_nodes_data: Dict[str, TransformerNodeData]
    transformer_tap_data: Dict[str, TransformerTapData]
