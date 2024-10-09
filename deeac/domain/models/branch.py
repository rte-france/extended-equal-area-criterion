# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Union, TYPE_CHECKING

from deeac.domain.exceptions import ParallelException
from .transformer import Transformer
from .line import Line
if TYPE_CHECKING:
    from .bus import Bus


class Branch:
    """
    Class modeling a branch (i.e. a set of parallel transformers or lines) between two nodes.
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
        Representation of a branch.
        """
        elements = ")(".join([f"{id}:{element}" for (id, element) in self.parallel_elements.items()])
        return f"Branch between nodes {self.first_bus.name} and {self.second_bus.name}: ({elements})"

    def __getitem__(self, parallel_id: str) -> Union[Line, Transformer]:
        """
        Define accessor to get an element based on its parallel ID.

        param parallel_id: Parallel ID of the element.
        return: The element at this parallel ID.
        """
        try:
            return self.parallel_elements[parallel_id]
        except KeyError:
            raise ParallelException(parallel_id, self.first_bus.name, self.second_bus.name)

    def __setitem__(self, parallel_index: str, element: Union[Line, Transformer]):
        """
        Define accessor to add or modify an element based on its parallel index.

        param parallel_index: Parallel index of the element.
        param breaker: New element for the corresponding parallel index.
        """
        self.parallel_elements[parallel_index] = element

    @property
    def closed(self) -> bool:
        """
        Return True if the branch is closed, False otherwise.
        A branch is closed if at least one of its parallel element is closed.

        return: True if the branch is closed, False otherwise.
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
