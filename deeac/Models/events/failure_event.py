"""
Module for failure_event.

:module: failure_event
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from abc import abstractmethod

from deeac.Models.bus import Bus
from deeac.Models.network import Network
from deeac.Models.events.event import Event


class FailureEvent(Event):
    """
    FailureEvent.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :summary: Class metadata.
    """

    @abstractmethod
    def get_nearest_bus(self, network: Network) -> Bus:
        """
        Get the bus that is the nearest to the fault.
        
        :param network: Network in which the bus must be found.
        :return: The nearest bus to the fault.
        """
        pass

