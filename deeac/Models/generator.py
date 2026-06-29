"""
Module for generator.

:module: generator
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

from deeac.Models.constants import BASE_POWER
from deeac.enums import BusType, GeneratorType, GeneratorSource


class Generator:
    """
    Generator.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar name: name.
    :ivar tpe: tpe.
    :ivar bus: bus.
    :ivar direct_transient_reactance: direct transient reactance.
    :ivar inertia_constant: inertia constant.
    :ivar active_power: active power.
    :ivar max_active_power: max active power.
    :ivar reactive_power: reactive power.
    :ivar connected: connected.
    :ivar source: source.
    :ivar regulating: regulating.
    """

    def __init__(
            self, name: str,
            tpe: GeneratorType,
            bus: 'Bus',
            direct_transient_reactance: float,
            inertia_constant: float,
            active_power: float,
            max_active_power: float,
            reactive_power: float,
            connected: bool = True,
            source: GeneratorSource = None,
            regulating: bool = False,
    ):
        """
        Initialize a generator.
        
        :param name: Name of the generator.
        :param tpe: Type of generator (PV or PQ).
        :param bus: Bus to which the generator is connected.
        :param direct_transient_reactance: Direct axis transient reactance of the generator. Unit: Ohm.
        :param inertia_constant: Constant of inertia of the generator. Unit: MWs / MVA
        :param active_power: Active power of the generator. Unit: MW.
        :param max_active_power: Maximum active power of the generator. Unit: MW.
        :param reactive_power: Reactive power of the generator. Unit: MVAr.
        :param target_voltage_magnitude: Target voltage magnitude applied by the generator in case of a PV generator.
        :param connected: True if the generator is connected to the network, False otherwise.
        :raise ZeroDirectTransientReactanceExeption if direct transient reactance is equal to 0.
        """
        self.name = name
        self.tpe = tpe
        self._bus = bus

        base_reactance = bus.base_voltage ** 2 / BASE_POWER
        self._direct_transient_reactance_pu = direct_transient_reactance / base_reactance
        self._inertia_constant = inertia_constant

        self._active_power_pu = active_power / BASE_POWER
        self._max_active_power_pu = max_active_power / BASE_POWER
        self._reactive_power_pu = reactive_power / BASE_POWER

        self.connected = connected
        self.source = source
        self.regulating = regulating

        # Compute properties
        self._complex_power = complex(self._active_power_pu, self._reactive_power_pu)
        try:
            self._direct_transient_admittance = 1 / complex(0, self._direct_transient_reactance_pu)
        except ZeroDivisionError:
            raise ValueError(name)
        self._internal_voltage = 0
        self._rotor_angle = 0
        self.compute_internal_voltage()

    def __repr__(self):
        """
        repr  .
        
        :return: Return value.
        """
        return (
            f"Generator: Name=[{self.name}] Type=[{self.tpe.name}] Bus=[{self._bus.name}] "
            f"x'd=[{self.direct_transient_reactance}] H=[{self._inertia_constant}] "
            f"P=[{self.active_power}] Pmax=[{self.max_active_power}]  "
            f"Q=[{self.reactive_power}] "
            f"Connected=[{self.connected}]"
        )

    def compute_internal_voltage(self):
        """
        Compute internal voltage.
        
        :return: Result value.
        """
        if self._bus.type == BusType.GEN_INT_VOLT:
            # Generator is connected to a fictive bus representing its internal voltage
            self._internal_voltage = self._bus.voltage
            return
        if self._bus.voltage == 0j:
            # Bus voltage is zero (disconnected from network)
            self._internal_voltage = 0j
            return
        # Compute conjugate of internal current (I = S / V)
        conj_current = np.conj(self._complex_power / self._bus.voltage)
        # E = V + jXI
        self._internal_voltage = complex(self._bus.voltage, self._direct_transient_reactance_pu * conj_current)
        # Get rotor angle
        self._rotor_angle = np.angle(self._internal_voltage)

    @property
    def bus(self) -> 'Bus':
        """
        Return the bus to the generator it is connected with
        
        :return: Thus connected bus.
        """
        return self._bus

    @bus.setter
    def bus(self, bus: 'Bus'):
        """
        Change the bus connected to the generator.
        
        :param bus: The new bus to which the generator is connected.
        """
        self._bus = bus
        self.compute_internal_voltage()

    @property
    def max_active_power_pu(self) -> float:
        """
        Max active power pu.
        
        :return: Return value.
        :rtype: float
        """
        return self._max_active_power_pu

    @property
    def max_active_power(self) -> float:
        """
        Max active power.
        
        :return: Return value.
        :rtype: float
        """
        return self._max_active_power_pu * BASE_POWER

    @max_active_power.setter
    def max_active_power(self, max_active_power: float):

        """
        Max active power.
        
        :param max_active_power: max active power.
        """
        self._max_active_power_pu = max_active_power / BASE_POWER


    @property
    def active_power_pu(self) -> float:
        """
        Active power pu.
        
        :return: Return value.
        :rtype: float
        """
        return self._active_power_pu

    @property
    def active_power(self) -> float:
        """
        Return the active power value.
        
        :return: The active power value in MW.
        """
        return self._active_power_pu * BASE_POWER

    @active_power.setter
    def active_power(self, active_power: float):
        """
        Active power.
        
        :param active_power: active power.
        """
        self._active_power_pu = active_power / BASE_POWER
        self._complex_power = complex(self._active_power_pu, self._reactive_power_pu)


    @property
    def reactive_power(self) -> float:
        """
        Return the reactive power value.
        
        :return: The reactive power value in MVAr.
        """
        return self._reactive_power_pu * BASE_POWER

    @reactive_power.setter
    def reactive_power(self, reactive_power: float):
        """
        Reactive power.
        
        :param reactive_power: reactive power.
        """
        self._reactive_power_pu = reactive_power / BASE_POWER
        self._complex_power = complex(self._active_power_pu, self._reactive_power_pu)


    @property
    def direct_transient_reactance_pu(self) -> float:
        """
        Return the direct transient reactance in per unit
        
        :return: Direct transient reactance in per unit.
        :raise DisconnectedElementException if the generator is disconnected.
        """
        if not self.connected:
            raise ValueError(repr(self), Generator.__name__)
        return self._direct_transient_reactance_pu

    @property
    def direct_transient_reactance(self) -> float:
        """
        Return the direct transient reactance
        
        :return: Direct transient reactance in Ohm.
        :raise DisconnectedElementException if the generator is disconnected.
        """
        if not self.connected:
            raise ValueError(repr(self), Generator.__name__)
        base_reactance = self.bus.base_voltage ** 2 / BASE_POWER
        return self._direct_transient_reactance_pu * base_reactance

    @property
    def direct_transient_admittance(self) -> complex:
        """
        Return the direct transient admittance.
        
        :return: Direct transient admittance (per unit).
        """
        return self._direct_transient_admittance if self.connected else 0j

    @property
    def complex_power(self) -> complex:
        """
        Complex power of the generator.
        
        :return: Complex power of the generator (per unit).
        """
        return self._complex_power if self.connected else 0j

    @property
    def internal_voltage(self) -> complex:
        """
        Internal voltage of the generator
        
        :return: Phasor corresponding to the internal voltage (per unit).
        """
        if not self.connected:
            # Generator is not connected
            return 0
        return self._internal_voltage

    @property
    def rotor_angle(self) -> float:
        """
        Rotor angle of the generator.
        It is equal to the internal angle in the pre-fault state.
        
        :return: Rotor angle (radian)
        """
        return self._rotor_angle if self.connected else 0

    @property
    def mechanical_power(self) -> float:
        """
        Mechanical power of the generator.
        
        :return: Mechanical power
        """
        return self.complex_power.real if self.connected else 0

    @property
    def inertia_coefficient(self) -> float:
        """
        Inertia coefficient of the generator.
        
        :return: The inertia coefficient.
        """
        return 2 * self._inertia_constant

    @property
    def inertia_constant(self) -> float:
        """
        Inertia constant.
        
        :return: Return value.
        :rtype: float
        """
        return self._inertia_constant

    @inertia_constant.setter
    def inertia_constant(self, inertia_constant: float):
        """
        Inertia constant.
        
        :param inertia_constant: inertia constant.
        """
        self._inertia_constant = inertia_constant


