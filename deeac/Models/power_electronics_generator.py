"""
Converter-based generator model.

:module: power_electronics_generator
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
from deeac.enums import GeneratorElectricalModel, GeneratorType, GeneratorSource


class PowerElectronicsGenerator(GeneratorInjectionParent):
    """
    Static power-electronics injection for converter-based renewable migration.
    """

    __slots__ = (
        "_electrical_model",
        "current",
        "admittance",
    )

    def __init__(
            self,
            name: str,
            tpe: GeneratorType,
            bus: "Bus",
            active_power: float,
            max_active_power: float,
            reactive_power: float,
            connected: bool = True,
            source: GeneratorSource = None,
            regulating: bool = False,
            electrical_model: GeneratorElectricalModel = GeneratorElectricalModel.CURRENT,
    ) -> None:
        """
        Initialize a static power-electronics generator.

        :param name: Generator name.
        :param tpe: Generator operating type.
        :param bus: Connected bus.
        :param active_power: Active power in MW.
        :param max_active_power: Maximum active power in MW.
        :param reactive_power: Reactive power in MVAr.
        :param connected: Connection state.
        :param source: Primary technology/source.
        :param regulating: Voltage-regulating flag.
        :param electrical_model: Electrical representation used in the network.
        :return: Return value.
        """
        # OMIB rationale:
        # This class exists because converter-based RES belongs to the
        # electrical world of OMIB, but not to the mechanical rotor-angle
        # world.
        #
        # In practice:
        # - it modifies the reduced network
        # - it may contribute explicit current-source terms
        # - it does not carry inertia or a rotor-angle trajectory
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
        self._electrical_model = electrical_model
        self.current = 0j
        self.admittance = 0j
        # Build the electrical view immediately because the rest of the OMIB
        # pipeline sees this object through current/admittance, not through a
        # synchronous internal-voltage abstraction.
        self._refresh_electrical_representation()

    def __repr__(self) -> str:
        """
        Get a readable representation for diagnostics.

        :return: Printable representation.
        """
        return (
            f"PowerElectronicsGenerator: Name=[{self.name}] Type=[{self.tpe.name}] Bus=[{self._bus.name}] "
            f"Model=[{self._electrical_model.name}] P=[{self.active_power}] Pmax=[{self.max_active_power}] "
            f"Q=[{self.reactive_power}] Connected=[{self.connected}]"
        )

    @property
    def electrical_model(self) -> GeneratorElectricalModel:
        """
        Get the electrical model category of the generator.

        :return: Electrical model category.
        """
        return self._electrical_model

    @electrical_model.setter
    def electrical_model(self, electrical_model: GeneratorElectricalModel) -> None:
        """
        Update the electrical model category of the generator.

        :param electrical_model: Electrical model category.
        :return: Return value.
        """
        # This switch is the heart of the RES theory split:
        # - LOAD   -> passive shunt-style representation
        # - CURRENT -> retained non-synchronous source representation
        self._electrical_model = electrical_model
        self._refresh_electrical_representation()

    def _on_bus_updated(self) -> None:
        """
        Recompute static source representation after a bus change.

        :return: Return value.
        """
        # OMIB rationale:
        # Converter-based RES is static, but still voltage-dependent in its
        # equivalent representation. Any bus-voltage change must refresh the
        # current/admittance seen by the reduced network.
        self._refresh_electrical_representation()

    def _on_power_updated(self) -> None:
        """
        Recompute static source representation after a power change.

        :return: Return value.
        """
        # OMIB rationale:
        # The static source is rebuilt from the latest P/Q injection because
        # OMIB consumes the resulting electrical footprint, not raw commands.
        self._refresh_electrical_representation()

    def _refresh_electrical_representation(self) -> None:
        """
        Rebuild current and admittance views for the chosen representation.

        :return: Return value.
        """
        if not self.connected or self._bus.voltage == 0j:
            # A disconnected converter source must disappear explicitly from
            # the reduced network, whichever RES model is selected.
            self.current = 0j
            self.admittance = 0j
        else:
            # Current-source side:
            # derive the injected complex current from S and V.
            # This is the quantity used when the RES bus is retained explicitly
            # in the current-source extension of the reduced admittance / OMIB.
            self.current = self.complex_power.conjugate() / self._bus.voltage.conjugate()
            if self._electrical_model == GeneratorElectricalModel.LOAD:
                if self._bus.voltage_magnitude_pu != 0:
                    # Load-model side:
                    # fold the same P/Q injection into a passive shunt
                    # admittance. In this mode the RES bus does not need to
                    # survive as an explicit source bus in the reduction.
                    self.admittance = np.conj(self.complex_power) / self._bus.voltage_magnitude_pu ** 2
                else:
                    self.admittance = 0j
            else:
                # Current-model side:
                # no passive shunt is added here because the source survives as
                # an explicit retained non-synchronous bus in the reduced model.
                self.admittance = 0j
        return None

    def refresh_electrical_representation(self) -> None:
        """
        Recompute the converter electrical representation explicitly.

        :return: Return value.
        """
        # Explicit public hook because bus/network refresh steps talk to this
        # class as a static OMIB-side source, not as a synchronous machine.
        self._refresh_electrical_representation()
