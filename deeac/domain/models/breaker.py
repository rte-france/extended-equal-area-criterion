# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.domain.exceptions import ParallelException
from .bus import Bus


class Breaker:
    """
    Breaker between two buses.
    """

    def __init__(self, closed: bool):
        """
        Initialize the breaker.

        :param closed: True if the breaker is closed, True otherwise.
        """
        self.closed = closed

    def __repr__(self):
        """
        Representation of a breaker.
        """
        return (
            f"Breaker: Closed=[{self.closed}]"
        )


class ParallelBreakers:
    """
    Set of parallel breakers between two buses.
    """

    def __init__(self, first_bus: Bus, second_bus: Bus):
        """
        Initialization.

        :param first_bus: First bus connected to the beaker.
        :param second_bus: Second bus connected to the beaker.
        """
        self._breakers = {}
        self.first_bus = first_bus
        self.second_bus = second_bus

    def __repr__(self):
        """
        Representation of parallel breakers.
        """
        breakers = "|".join([f"{id}:CLOSED" if br.closed else f"{id}:OPENED" for (id, br) in self._breakers.items()])
        return (
            f"Parallel breakers: Bus1=[{self.first_bus.name}] Bus2=[{self.second_bus.name}] Breakers=[{breakers}]"
        )

    def __getitem__(self, parallel_id: str) -> Breaker:
        """
        Define accessor to get a breaker based on its parallel ID.

        param parallel_id: Parallel ID of the breaker.
        return: The breaker at this parallel ID.
        """
        try:
            return self._breakers[parallel_id]
        except KeyError:
            raise ParallelException(parallel_id, self.first_bus.name, self.second_bus.name)

    def __setitem__(self, parallel_index: str, breaker: Breaker):
        """
        Define accessor to add or modify a breaker based on its parallel index.

        param parallel_index: Parallel index of the breaker.
        param breaker: New breaker for the corresponding parallel index.
        """
        self._breakers[parallel_index] = breaker

    @property
    def closed(self) -> bool:
        """
        Determine if at least one of the parallel breakers is closed.

        :return: True if at least one of the breakers is closed.
        """
        for breaker in self._breakers.values():
            if breaker.closed:
                return True
        return False
