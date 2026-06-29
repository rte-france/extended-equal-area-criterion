"""
Module for branch.

:module: branch
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Union, TYPE_CHECKING

from deeac.Models.transformer import Transformer
from deeac.Models.line import Line
if TYPE_CHECKING:
    from deeac.Models.bus import Bus


class Branch:
    """
    Branch.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar first_bus: first bus.
    :ivar second_bus: second bus.
    """

    def __init__(self, first_bus: 'Bus', second_bus: 'Bus'):
        """
        Initialize the branch without parallel elements.
        
        :param first_bus: Sending bus.
        :param second_bus: Receiving bus.
        """
        self.first_bus = first_bus
        self.second_bus = second_bus
        self.parallel_elements = {}

    def __repr__(self):
        """
        repr  .
        
        :return: Return value.
        """
        elements = ")(".join([f"{id_}:{element}" for (id_, element) in self.parallel_elements.items()])
        return f"Branch between nodes {self.first_bus.name} and {self.second_bus.name}: ({elements})"

    def __getitem__(self, parallel_id: str) -> Union[Line, Transformer]:
        """
        getitem  .
        
        :param parallel_id: parallel id.
        """
        try:
            return self.parallel_elements[parallel_id]
        except KeyError:
            raise ValueError(parallel_id, self.first_bus.name, self.second_bus.name)

    def __setitem__(self, parallel_index: str, element: Union[Line, Transformer]):
        """
        setitem  .
        
        :param parallel_index: parallel index.
        :param element: element.
        """
        self.parallel_elements[parallel_index] = element

    @property
    def closed(self) -> bool:
        """
        Closed.
        
        :return: Return value.
        :rtype: bool
        """
        for element in self.parallel_elements.values():
            if element.closed:
                return True
        return False

    @property
    def admittance(self) -> complex:
        """
        Compute the total admittance of this branch.
        
        :return: The admittance as a complex (per unit).
        """
        return sum([element.admittance for element in self.parallel_elements.values()])

    @property
    def shunt_admittance(self) -> complex:
        """
        Compute the shunt admittance of the branch.
        
        :return: The shunt admittance of the branch, as a complex (per unit).
        """
        return sum(element.shunt_admittance for element in self.parallel_elements.values())
