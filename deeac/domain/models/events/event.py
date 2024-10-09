# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from abc import ABC, abstractmethod

from deeac.domain.ports.dtos.events import Event as EventDto
from deeac.domain.models import Network


class Event(ABC):
    """
    Class that models an event in a distribution network
    """

    @classmethod
    @abstractmethod
    def create_event(cls, event_data: EventDto) -> 'Event':
        """
        Create an event based on input event data.

        :param event_data: The event data.
        :return: An event based on the event data.
        """
        pass

    @abstractmethod
    def apply_to_network(self, network: Network):
        """
        Apply the event to the network given as argument.
        This method modifies the network given as argument according to the event.

        :param network: The network to which the event must be applied.
        """
        pass
