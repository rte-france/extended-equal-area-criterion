"""
Module for transformer.

:module: transformer

# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.
"""
from __future__ import annotations


class Transformer:
    """
    Transformer.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar _base_impedance: base impedance.
    :ivar _resistance_pu: resistance in per-unit.
    :ivar _reactance_pu: reactance in per-unit.
    :ivar _shunt_susceptance_pu: shunt susceptance in per-unit.
    :ivar _shunt_conductance_pu: shunt conductance in per-unit.
    :ivar _phase_shift_angle: phase shift angle.
    :ivar ratio: branch rated power (MVA).
    :ivar initial_tap_number: initial tap number.
    :ivar closed_at_first_bus: closed at first bus.
    :ivar closed_at_second_bus: closed at second bus.
    :ivar sending_node: sending node.
    :ivar receiving_node: receiving node.
    :ivar transformer_type: transformer type.
    """

    __slots__ = (
        "_base_impedance",
        "_resistance_pu",
        "_reactance_pu",
        "_shunt_susceptance_pu",
        "_shunt_conductance_pu",
        "_phase_shift_angle",
        "ratio",
        "initial_tap_number",
        "closed_at_first_bus",
        "closed_at_second_bus",
        "sending_node",
        "receiving_node",
        "transformer_type",
    )

    def __init__(self,
                 base_impedance: float | None = None,
                 resistance: float = 0.0,
                 reactance: float = 0.0,
                 shunt_susceptance: float = 0.0,
                 shunt_conductance: float = 0.0,
                 phase_shift_angle: float | None = None,
                 ratio: float | None = None,
                 initial_tap_number: int | None = None,
                 closed_at_first_bus: bool = True,
                 closed_at_second_bus: bool = True,
                 sending_node: str | None = None,
                 receiving_node: str | None = None,
                 transformer_type: int | None = None):
        """
        Initialize the transformer. The primary side is connected to the first bus of the branch, while the secondary
        side connected to the second bus.
        
        :param resistance: Transformer resistance.
        :param reactance: Transformer reactance.
        :param shunt_susceptance: Transformer shunt susceptance.
        :param shunt_conductance: Transformer shunt conductance.
        :param base_impedance: Base impedance for pu.
        :param phase_shift_angle: Phase shift angle associated to the tap. unit: Rad.
        :param ratio: Branch rated power (MVA)
        :param closed_at_first_bus: True if the line is closed at the primary side, False otherwise.
        :param closed_at_second_bus: True if the line is closed at the secondary side, False otherwise.
        :param sending_node: id of the sending node
        :param receiving_node: id of the receiving node
        :param transformer_type: Transformer 1 or Transformer 8
        """
        self._base_impedance = base_impedance
        self._resistance_pu = resistance / base_impedance
        self._reactance_pu = reactance / base_impedance
        self._shunt_susceptance_pu = shunt_susceptance * base_impedance
        self._shunt_conductance_pu = shunt_conductance * base_impedance

        self._phase_shift_angle = phase_shift_angle
        self.ratio = ratio
        self.initial_tap_number = initial_tap_number
        self.closed_at_first_bus = closed_at_first_bus
        self.closed_at_second_bus = closed_at_second_bus
        self.sending_node = sending_node
        self.receiving_node = receiving_node
        self.transformer_type = transformer_type  # TODO must not be present here!

    def __repr__(self) -> str:
        """
        repr  .
        
        :return: Return value.
        """
        return (
            f"Transformer: "
            f"R=[{self._resistance_pu}] "
            f"X=[{self._reactance_pu}] "
            f"phase shift angle=[{self._phase_shift_angle}] "
            f"Closed at primary=[{self.closed_at_first_bus}] "
            f"Closed at secondary=[{self.closed_at_second_bus}]"
        )

    @property
    def phase_shift_angle(self) -> float | None:
        """
        Phase shift angle.
        
        :return: Phase shift angle (in rad)
        """
        return self._phase_shift_angle if self._phase_shift_angle is not None else None

    @phase_shift_angle.setter
    def phase_shift_angle(self, value: float | None) -> None:
        """
        Phase shift angle.
        
        :param value: value.
        """
        self._phase_shift_angle = value

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
            raise ValueError()
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
            raise ValueError()
        return complex(self._shunt_conductance_pu, -1 * self._shunt_susceptance_pu)

    @property
    def resistance(self) -> float:
        """
        Transformer resistance.
        
        :return: Transformer resistance (Ohm)
        """
        return self._resistance_pu * self._base_impedance

    @resistance.setter
    def resistance(self, resistance: float):
        """
        Resistance.
        
        :param resistance: resistance.
        """
        self._resistance_pu = resistance / self._base_impedance

    @property
    def reactance(self) -> float:
        """
        Transformer reactance.
        
        :return: Transformer reactance (Ohm)
        """
        return self._reactance_pu * self._base_impedance

    @reactance.setter
    def reactance(self, reactance: float):
        """
        Reactance.
        
        :param reactance: reactance.
        """
        self._reactance_pu = reactance / self._base_impedance

    @property
    def shunt_conductance(self) -> float:
        """
        Transformer shunt conductance.
        
        :return: Transformer shunt conductance (S)
        """
        return self._shunt_conductance_pu / self._base_impedance

    @shunt_conductance.setter
    def shunt_conductance(self, shunt_conductance: float):
        """
        Shunt conductance.
        
        :param shunt_conductance: shunt conductance.
        """
        self._shunt_conductance_pu = shunt_conductance * self._base_impedance

    @property
    def shunt_susceptance(self) -> float:
        """
        Transformer shunt susceptance.
        
        :return: Transformer shunt susceptance (S)
        """
        return self._shunt_susceptance_pu / self._base_impedance

    @shunt_susceptance.setter
    def shunt_susceptance(self, shunt_susceptance: float):
        """
        Shunt susceptance.
        
        :param shunt_susceptance: shunt susceptance.
        """
        self._shunt_susceptance_pu = shunt_susceptance * self._base_impedance

    @property
    def base_impedance(self) -> float:
        """
        Base impedance.
        
        :return: Return value.
        :rtype: float
        """
        return self._base_impedance

    @base_impedance.setter
    def base_impedance(self, base_impedance: float):
        """
        Base impedance.
        
        :param base_impedance: base impedance.
        """
        old_base_impedance = self._base_impedance
        self._base_impedance = base_impedance
        self._shunt_conductance_pu *= self._base_impedance / old_base_impedance
        self._shunt_susceptance_pu *= self._base_impedance / old_base_impedance
        self._reactance_pu *= old_base_impedance / self._base_impedance
        self._resistance_pu *= old_base_impedance / self._base_impedance
