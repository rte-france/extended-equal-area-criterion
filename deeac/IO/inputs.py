"""
EEAC input models.

:module: inputs
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Optional

from deeac.Models.network import Network, NetworkComputed
from deeac.Models.generator_snapshot import GeneratorSnapshot


class EEACInputs:
    """
    EEAC input container.
    
    Rationale:
        This class is part of the EEAC orchestration layer. It wires configuration
        to the identifier/evaluator/selector steps and formats or transports the
        results through the execution pipeline.
    
    :ivar generator_snapshot: Generator snapshot available for EEAC.
    :ivar network: Network instance for EEAC.
    :ivar computed: Computed network cache.
    :ivar output_dir: Output directory for node results.
    """

    def __init__(
        self,
        generator_snapshot: GeneratorSnapshot,
        network: Network,
        computed: NetworkComputed,
        output_dir: Optional[str],
    ) -> None:
        """
        Initialize the EEAC inputs.
        
        :param generator_snapshot: Generator snapshot available for EEAC.
        :param network: Network instance for EEAC.
        :param computed: Computed network cache.
        :param output_dir: Output directory for node results.
        :return: Return value.
        """
        self.generator_snapshot = generator_snapshot
        self.network = network
        self.computed = computed
        self.output_dir = output_dir
