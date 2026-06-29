"""
Module for fault_events.

:module: fault_events
"""
# Copyright (c) 2020-2025, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List, Optional, Sequence

from deeac.Models.events.failure_event import FailureEvent
from deeac.Models.events.mitigation_event import MitigationEvent


class FaultEvents:
    """
    FaultEvents.

    Rationale:
        This class groups the failure and mitigation events for a single
        contingency (e.g., one .seq file).
    """

    def __init__(
        self,
        failure_events: Sequence[FailureEvent],
        mitigation_events: Sequence[MitigationEvent],
        name: Optional[str] = None,
        short_circuit_delay: Optional[float] = None,
    ) -> None:
        """
        Initialize the fault event bundle.

        :param failure_events: Failure events.
        :param mitigation_events: Mitigation events.
        :param name: Optional fault name.
        :param short_circuit_delay: Optional protection delay in ms.
        """
        self.failure_events: List[FailureEvent] = list(failure_events)
        self.mitigation_events: List[MitigationEvent] = list(mitigation_events)
        self.name = name
        self.short_circuit_delay = short_circuit_delay

