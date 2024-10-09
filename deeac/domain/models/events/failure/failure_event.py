# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from abc import abstractmethod

from deeac.domain.models import Network, Bus
from deeac.domain.models.events import Event


class FailureEvent(Event):
    """
    Class that models failure event.
    """

    @abstractmethod
    def get_nearest_bus(self, network: Network) -> Bus:
        """
        Get the bus that is the nearest to the fault.

        :param network: Network in which the bus must be found.
        :return: The nearest bus to the fault.
        """
        pass
