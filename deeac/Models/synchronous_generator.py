"""
Synchronous generator model.

:module: synchronous_generator
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
import numpy as np

if TYPE_CHECKING:
    from deeac.Models.bus import Bus

from deeac.Models.generator_injection_parent import GeneratorInjectionParent
from deeac.Models.constants import BASE_POWER
from deeac.enums import BusType, GeneratorElectricalModel, GeneratorType, GeneratorSource


class SynchronousGenerator(GeneratorInjectionParent):
    """
    Classical synchronous generator used by the OMIB pipeline.
    """

    __slots__ = (
        "_direct_transient_reactance_pu",
        "_inertia_constant",
        "_direct_transient_admittance",
        "_internal_voltage",
        "_rotor_angle",
    )

    def __init__(
            self,
            name: str,
            tpe: GeneratorType,
            bus: "Bus",
            direct_transient_reactance: float,
            inertia_constant: float,
            active_power: float,
            max_active_power: float,
            reactive_power: float,
            connected: bool = True,
            source: GeneratorSource = None,
            regulating: bool = False,
    ) -> None:
        """
        Initialize a synchronous generator.

        :param name: Generator name.
        :param tpe: Generator operating type.
        :param bus: Connected bus.
        :param direct_transient_reactance: Direct transient reactance in ohm.
        :param inertia_constant: Inertia constant.
        :param active_power: Active power in MW.
        :param max_active_power: Maximum active power in MW.
        :param reactive_power: Reactive power in MVAr.
        :param connected: Connection state.
        :param source: Primary technology/source.
        :param regulating: Voltage-regulating flag.
        :return: Return value.
        """
        # OMIB rationale:
        # This is the only generator class that belongs to the dynamic core of
        # the classical EEAC/OMIB model. A synchronous machine contributes:
        # - inertia to the swing-equation side
        # - an internal voltage behind transient reactance to the electrical side
        #
        # That is why this class carries both mechanical metadata
        # (inertia_constant) and electrical metadata
        # (direct_transient_reactance / internal_voltage).
        super().__init__(
            name=name,
            tpe=tpe,
            bus=bus,
            active_power=active_power,
            max_active_power=max_active_power,
            reactive_power=reactive_power,
            connected=connected,
            source=source,
            regulating=regulating,
        )
        base_reactance: float = bus.base_voltage ** 2 / BASE_POWER
        self._direct_transient_reactance_pu = direct_transient_reactance / base_reactance
        self._inertia_constant = inertia_constant
        try:
            self._direct_transient_admittance = 1 / complex(0, self._direct_transient_reactance_pu)
        except ZeroDivisionError:
            raise ValueError(name)
        self._internal_voltage = 0j
        self._rotor_angle = 0.0
        # The internal EMF is the quantity actually used when the classical
        # network is reduced for OMIB. We therefore compute it immediately.
        self.compute_internal_voltage()

    def __repr__(self) -> str:
        """
        Return a readable diagnostic representation.

        :return: Printable representation.
        """
        return (
            f"SynchronousGenerator: Name=[{self.name}] Type=[{self.tpe.name}] Bus=[{self._bus.name}] "
            f"x'd=[{self.direct_transient_reactance}] H=[{self._inertia_constant}] "
            f"P=[{self.active_power}] Pmax=[{self.max_active_power}] "
            f"Q=[{self.reactive_power}] Connected=[{self.connected}]"
        )

    def _on_bus_updated(self) -> None:
        """
        Recompute synchronous internal state after a bus change.

        :return: Return value.
        """
        # OMIB rationale:
        # A synchronous generator is not represented in OMIB by its terminal
        # voltage directly. It is represented by an internal EMF behind Xd'.
        # As soon as the bus changes, that equivalent source must be rebuilt.
        self.compute_internal_voltage()

    def _on_power_updated(self) -> None:
        """
        Recompute synchronous internal state after a power change.

        :return: Return value.
        """
        # OMIB rationale:
        # Changing P/Q changes the current flowing at the machine terminals,
        # which changes the inferred internal EMF used by the reduced-network
        # and OMIB electrical-power expressions.
        self.compute_internal_voltage()

    def compute_internal_voltage(self) -> None:
        """
        Compute internal voltage from the classical synchronous model.

        :return: Return value.
        """
        if self._bus.type == BusType.GEN_INT_VOLT:
            # In the simplified OMIB network, a fictive internal-voltage bus
            # may already represent the machine source directly. In that case
            # there is no need to infer E from terminal quantities: the bus is
            # already the internal source.
            self._internal_voltage = self._bus.voltage
            self._rotor_angle = np.angle(self._internal_voltage)
        else:
            if self._bus.voltage == 0j:
                # A disconnected bus means the machine is electrically absent
                # from the network seen by OMIB, so the equivalent source must
                # collapse explicitly to zero.
                self._internal_voltage = 0j
                self._rotor_angle = 0
            else:
                # Classical machine reduction:
                # - derive terminal current from S and V
                # - push that current through j Xd'
                # - recover the internal EMF E
                #
                # This E is exactly the source amplitude/angle later consumed
                # by the reduced admittance and OMIB electrical power law.
                conj_current: complex = np.conj(self._complex_power / self._bus.voltage)
                self._internal_voltage = complex(
                    self._bus.voltage,
                    self._direct_transient_reactance_pu * conj_current,
                )
                self._rotor_angle = np.angle(self._internal_voltage)
        return None

    @property
    def electrical_model(self) -> GeneratorElectricalModel:
        """
        Get the electrical model category of the generator.

        :return: Synchronous electrical model.
        """
        return GeneratorElectricalModel.SYNCHRONOUS

    @property
    def direct_transient_reactance_pu(self) -> float:
        """
        Get the direct transient reactance in per unit.

        :return: Direct transient reactance in per unit.
        """
        if not self.connected:
            raise ValueError(repr(self), SynchronousGenerator.__name__)
        else:
            return self._direct_transient_reactance_pu

    @property
    def direct_transient_reactance(self) -> float:
        """
        Get the direct transient reactance in ohm.

        :return: Direct transient reactance in ohm.
        """
        if not self.connected:
            raise ValueError(repr(self), SynchronousGenerator.__name__)
        else:
            base_reactance: float = self.bus.base_voltage ** 2 / BASE_POWER
            return self._direct_transient_reactance_pu * base_reactance

    @property
    def direct_transient_admittance(self) -> complex:
        """
        Get the direct transient admittance in per unit.

        :return: Direct transient admittance in per unit.
        """
        if self.connected:
            return self._direct_transient_admittance
        else:
            return 0j

    @property
    def internal_voltage(self) -> complex:
        """
        Get the internal voltage phasor in per unit.

        :return: Internal voltage phasor.
        """
        if not self.connected:
            return 0
        else:
            return self._internal_voltage

    @property
    def rotor_angle(self) -> float:
        """
        Get the rotor angle in radian.

        :return: Rotor angle in radian.
        """
        if self.connected:
            return self._rotor_angle
        else:
            return 0

    @property
    def mechanical_power(self) -> float:
        """
        Get the mechanical power in per unit.

        :return: Mechanical power in per unit.
        """
        # OMIB rationale:
        # Mechanical power is only meaningful for synchronous machines because
        # only they participate in the rotor-angle swing dynamics.
        if self.connected:
            return self.complex_power.real
        else:
            return 0

    @property
    def inertia_coefficient(self) -> float:
        """
        Get the inertia coefficient used by the swing equation.

        :return: Inertia coefficient.
        """
        # This quantity exists because OMIB aggregates synchronous machines by
        # inertia weighting. Converter-based sources do not contribute here.
        return 2 * self._inertia_constant

    @property
    def inertia_constant(self) -> float:
        """
        Get the inertia constant.

        :return: Inertia constant.
        """
        return self._inertia_constant

    @inertia_constant.setter
    def inertia_constant(self, inertia_constant: float) -> None:
        """
        Update the inertia constant.

        :param inertia_constant: Inertia constant.
        :return: Return value.
        """
        self._inertia_constant = inertia_constant
