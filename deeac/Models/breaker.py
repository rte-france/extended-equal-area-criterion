"""
Module for breaker.

:module: breaker
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from deeac.Models.bus import Bus


class Breaker:
    """
    Breaker.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar closed: closed.
    """

    def __init__(self, closed: bool):
        """
        Initialize the breaker.
        
        :param closed: True if the breaker is closed, True otherwise.
        """
        self.closed = closed

    def __repr__(self):
        """
        repr  .
        
        :return: Return value.
        """
        return (
            f"Breaker: Closed=[{self.closed}]"
        )


class ParallelBreakers:
    """
    Parallelbreakers.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar first_bus: first bus.
    :ivar second_bus: second bus.
    """

    def __init__(self, first_bus: 'Bus', second_bus: 'Bus'):
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
        repr  .
        
        :return: Return value.
        """
        breakers = "|".join([f"{id}:CLOSED" if br.closed else f"{id}:OPENED" for (id, br) in self._breakers.items()])
        return (
            f"Parallel breakers: Bus1=[{self.first_bus.name}] Bus2=[{self.second_bus.name}] Breakers=[{breakers}]"
        )

    def __getitem__(self, parallel_id: str) -> Breaker:
        """
        getitem  .
        
        :param parallel_id: parallel id.
        """
        try:
            return self._breakers[parallel_id]
        except KeyError:
            raise ValueError(parallel_id, self.first_bus.name, self.second_bus.name)

    def __setitem__(self, parallel_index: str, breaker: Breaker):
        """
        setitem  .
        
        :param parallel_index: parallel index.
        :param breaker: breaker.
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
