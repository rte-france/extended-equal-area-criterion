# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.domain.exceptions import DEEACException


class NetworkElementNameException(DEEACException):
    """
    Exception raised when multiple network elements of the same type have the same name, while it should be unique.
    """

    def __init__(self, name: str, element_type: str):
        """
        Initialization.

        :param name: Duplicated name.
        :param element_type: Type of the duplicated element.
        """
        self.name = name
        self.element_type = element_type

    def __str__(self):
        """
        Return a string representation of the exception.
        """
        return (
            f"Multiple elements of type {self.element_type} have the same name {self.name}"
        )


class BranchParallelException(DEEACException):
    """
    Exception raised when two parallel elements in a branch have the same parallel ID.
    """

    def __init__(self, sending_bus: str, receiving_bus: str, parallel_id: str):
        """
        Initialization.

        :param sending_bus: Sending bus of the branch.
        :param receiving_bus: Receiving bus of the branch.
        :param receiving_bus: Duplicated parallel ID.
        """
        self.sending_bus = sending_bus
        self.receiving_bus = receiving_bus
        self.parallel_id = parallel_id

    def __str__(self):
        """
        Return a string representation of the exception.
        """
        return (
            f"Branch from bus {self.sending_bus} to bus {self.receiving_bus} has elements with same parallel "
            f"ID {self.parallel_id}."
        )


class TapNumberException(DEEACException):
    """
    Exception raised when a tap position appears 2 times in an input topology.
    """

    def __init__(self, tap_number: int, sending_bus: str, receiving_bus: str, parallel_id: str):
        """
        Initialization.

        :param tap_number: Tap position appearing 2 times.
        :param sending_bus: Sending bus of the branch.
        :param receiving_bus: Receiving bus of the branch.
        :param receiving_bus: Duplicated parallel ID.
        """
        self.tap_number = tap_number
        self.sending_bus = sending_bus
        self.receiving_bus = receiving_bus
        self.parallel_id = parallel_id

    def __str__(self):
        """
        Return a string representation of the exception.
        """
        return (
            f"Tap data associated to tap number {self.tap_number} specified multiple times for transformer in branch "
            f"from bus {self.sending_bus} to bus {self.receiving_bus} with parallel ID {self.parallel_id}."
        )


class NominalTapException(DEEACException):
    """
    Exception raised when a nominal tap cannot be found.
    """

    def __init__(self, nominal_tap_number: int, sending_bus: str, receiving_bus: str, parallel_id: str):
        """
        Initialization.

        :param nominal_tap_number: Nominal tap position.
        :param sending_bus: Sending bus of the branch.
        :param receiving_bus: Receiving bus of the branch.
        :param receiving_bus: Duplicated parallel ID.
        """
        self.nominal_tap_number = nominal_tap_number
        self.sending_bus = sending_bus
        self.receiving_bus = receiving_bus
        self.parallel_id = parallel_id

    def __str__(self):
        """
        Return a string representation of the exception.
        """
        return (
            f"No tap data associated to nominal ta number {self.nominal_tap_number} for transformer in branch "
            f"from bus {self.sending_bus} to bus {self.receiving_bus} with parallel ID {self.parallel_id}."
        )
