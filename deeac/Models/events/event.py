"""
Module for event.

:module: event
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from abc import ABC, abstractmethod

from deeac.Models.network import Network


class Event(ABC):
    """
    Event.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :summary: Class metadata.
    """

    @abstractmethod
    def apply_to_network(self, network: Network):
        """
        Apply the event to the network given as argument.
        This method modifies the network given as argument according to the event.
        
        :param network: The network to which the event must be applied.
        """
        pass
