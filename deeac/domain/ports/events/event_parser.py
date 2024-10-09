# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List
from abc import ABC, abstractmethod

from deeac.domain.ports.dtos.events import Event


class EventParser(ABC):
    """
    Abstract class gathering methods to read events from an input file.
    """

    @abstractmethod
    def parse_events(self) -> List[Event]:
        """
        Parse events from input.

        :return: The list of events extracted from the input.
        """
        pass
