# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.domain.exceptions import TransformerImpedanceException


class Transformer:
    """
    Transformer in a network.
    """

    def __init__(
        self, base_impedance = None,
        resistance: float = None, reactance: float = None,
        shunt_susceptance: float = None, shunt_conductance: float = None,
        phase_shift_angle: float = None, ratio: float = None,
        closed_at_first_bus: bool = True, closed_at_second_bus: bool = True,
        sending_node: str = None, receiving_node: str = None, transformer_type: int = None
    ):
        """
        Initialize the transformer. The primary side is connected to the first bus of the branch, while the secondary
        side connected to the second bus.

        :param resistance: Transformer resistance.
        :param reactance: Transformer reactance.
        :param shunt_susceptance: Transformer shunt susceptance.
        :param shunt_conductance: Transformer shunt conductance.
        :param base_impedance: Base impedance for pu.
        :param phase_shift_angle: Phase shift angle associated to the tap. unit: Rad.
        :param ratio:
        :param closed_at_first_bus: True if the line is closed at the primary side, False otherwise.
        :param closed_at_second_bus: True if the line is closed at the secondary side, False otherwise.
        :param sending_node:
        :param receiving_node:
        :param transformer_type: Transformer 1 or Transformer 8
        """
        self._base_impedance = base_impedance
        self._resistance_pu = resistance / base_impedance
        self._reactance_pu = reactance / base_impedance
        self._shunt_susceptance_pu = shunt_susceptance * base_impedance
        self._shunt_conductance_pu = shunt_conductance * base_impedance

        self._phase_shift_angle = phase_shift_angle
        self.ratio = ratio
        self.closed_at_first_bus = closed_at_first_bus
        self.closed_at_second_bus = closed_at_second_bus
        self.sending_node = sending_node
        self.receiving_node = receiving_node
        self.transformer_type = transformer_type  # TODO must not be present here!

    def __repr__(self):
        """
        Representation of a transformer.
        """
        return (
            f"Transformer: R=[{self._resistance}] X=[{self._reactance}] phase shift angle=[{self._phase_shift_angle}] "
            f"Closed at primary=[{self.closed_at_first_bus}] Closed at secondary=[{self.closed_at_second_bus}]"
        )

    @property
    def phase_shift_angle(self):
        """
        Phase shift angle.

        :return: Phase shift angle (in rad)
        """
        return self._phase_shift_angle if self._phase_shift_angle is not None else None

    @property
    def closed(self) -> bool:
        """
        Determine if the transformer is closed.

        :return: True if the transformer is closed at both sides, False otherwise.
        """
        return self.closed_at_first_bus and self.closed_at_second_bus

    @property
    def impedance(self) -> complex:
        """
        Impedance of the transformer

        :return: Transformer impedance (per unit)
        :raise: DisconnectedElementException if the transformer is opened.
        """
        if self._resistance_pu is None or self._reactance_pu is None:
            # No load flow data were loaded for this transformer
            raise TransformerImpedanceException()
        return complex(self._resistance_pu, self._reactance_pu)

    @property
    def admittance(self) -> complex:
        """
        Admittance of the transformer

        :return: Transformer admittance (per unit)
        """
        return 1 / self.impedance

    @property
    def shunt_admittance(self) -> complex:
        """
        Transformer shunt admittance.

        :return: Shunt admittance of the transformer (per unit)
        :raise: DisconnectedElementException if the transformer is opened.
        """
        if self._resistance_pu is None or self._reactance_pu is None:
            # No load flow data were loaded for this transformer
            raise TransformerImpedanceException()
        return complex(self._shunt_conductance_pu, -1 * self._shunt_susceptance_pu)

    @property
    def resistance(self) -> float:
        """
        Transformer resistance.

        :return: Transformer resistance (Ohm)
        """
        return self._resistance_pu * self._base_impedance

    @property
    def reactance(self) -> float:
        """
        Transformer reactance.

        :return: Transformer reactance (Ohm)
        """
        return self.reactance_pu * self._base_impedance

    @property
    def shunt_conductance(self) -> float:
        """
        Transformer shunt conductance.

        :return: Transformer shunt conductance (S)
        """
        return self._shunt_conductance_pu / self._base_impedance

    @property
    def shunt_susceptance(self) -> float:
        """
        Transformer shunt susceptance.

        :return: Transformer shunt susceptance (S)
        """
        return self._shunt_susceptance_pu / self._base_impedance

