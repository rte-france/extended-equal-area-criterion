# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.


class Line:
    """
    Line in a network.
    """

    def __init__(
        self, base_impedance,
        resistance: float, reactance: float, shunt_conductance: float, shunt_susceptance: float,
        closed_at_first_bus: bool = True, closed_at_second_bus: bool = True
    ):
        """
        Initialize a line.

        :param resistance: Resitance of the line.
        :param reactance: Reactance of the line.
        :param shunt_conductance: Shunt conductance of the line.
        :param shunt_susceptance: Shunt susceptance of the line.
        :param base_impedance: Base impedance for pu.
        :param closed_at_first_bus: True if the line is closed at the first bus, False otherwise.
        :param closed_at_second_bus: True if the line is closed at the second bus, False otherwise.
        """
        self._base_impedance = base_impedance
        self._resistance_pu = resistance / base_impedance
        self._reactance_pu = reactance / base_impedance
        self._shunt_conductance_pu = shunt_conductance * base_impedance
        self._shunt_susceptance_pu = shunt_susceptance * base_impedance
        self.closed_at_first_bus = closed_at_first_bus
        self.closed_at_second_bus = closed_at_second_bus
        self.metal_short_circuited = False

    def __repr__(self):
        """
        Representation of a line.
        """
        return (
            f"Line: R=[{self.resistance}] X=[{self.reactance}] Gs=[{self.shunt_conductance}] "
            f"Bs=[{self.shunt_susceptance}] Closed at first bus=[{self.closed_at_first_bus}] Closed at second bus="
            f"[{self.closed_at_second_bus}] Metal short circuit=[{self.metal_short_circuited}]"
        )

    @property
    def closed(self) -> bool:
        """
        Determine if the line is closed.

        :return: True if the line is closed at both sides, and not short circuited, False otherwise.
        """
        return not self.metal_short_circuited and self.closed_at_first_bus and self.closed_at_second_bus

    @property
    def open(self) -> bool:
        """
        Determine if the line is closed.

        :return: True if the line is closed at one side only, and not short circuited, False otherwise.
        """
        return not self.metal_short_circuited and (self.closed_at_first_bus ^ self.closed_at_second_bus)

    @property
    def impedance_pu(self) -> complex:
        """
        Line impedance

        :return: Line impedance (per unit)
        """
        return complex(self._resistance_pu, self._reactance_pu)

    @property
    def admittance_pu(self) -> complex:
        """
        Line admittance

        :return: Line admittance (per unit)
        """
        return 1 / self.impedance_pu

    @property
    def shunt_admittance_pu(self) -> complex:
        """
        Line shunt admittance.

        :return: Shunt admittance of the line (per unit)
        """
        return complex(self._shunt_conductance_pu, self._shunt_susceptance_pu)

    @property
    def resistance(self) -> float:
        """
        line resistance.

        :return: Line resistance (Ohm)
        """
        return self._resistance_pu * self._base_impedance

    @property
    def reactance(self) -> float:
        """
        line reactance.

        :return: Line reactance (Ohm)
        """
        return self.reactance_pu * self._base_impedance

    @property
    def shunt_conductance(self) -> float:
        """
        line shunt conductance.

        :return: Line shunt conductance (S)
        """
        return self._shunt_conductance_pu / self._base_impedance

    @property
    def shunt_susceptance(self) -> float:
        """
        line shunt susceptance.

        :return: Line shunt susceptance (S)
        """
        return self._shunt_susceptance_pu / self._base_impedance
