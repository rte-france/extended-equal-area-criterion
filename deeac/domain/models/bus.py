# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import cmath
import numpy as np
from enum import Enum
from typing import Set

from .load import Load
from .capacitor_bank import CapacitorBank
from .generator import Generator, GeneratorType
from .value import Value, Unit, PUBase
from .branch import Branch

from deeac.domain.exceptions import CoupledBusesException, BusVoltageException


class BusType(Enum):
    PQ = "PQ"
    PV = "PV"
    SLACK = "SLACK"
    GEN_INT_VOLT = "GENERATOR_INTERNAL_VOLTAGE"


class Bus:
    """
    Bus (node) in the network.
    """

    def __init__(
        self, name: str, base_voltage: float, voltage_magnitude: Value = None, phase_angle: float = None,
        type: BusType = None
    ):
        """
        Initialize a bus.

        :param name: Name of the bus.
        :param base_voltage: Base voltage for per unit conversions. Unit: kV.
        :param voltage_magnitude: Voltage magnitude at the bus. Unit: kV.
        :param phase_angle: Phase angle at the bus. Unit: rad.
        :param type: Type of the bus. If None, the type is derived from the connected generators.
        """
        self.name = name
        self.branches = []
        self.generators = []
        self.loads = []
        self.capacitor_banks = []
        self.base_voltage = base_voltage
        self._type = type
        self._voltage_magnitude = voltage_magnitude
        self._voltage_magnitude_pu = voltage_magnitude / base_voltage
        self._phase_angle = phase_angle
        self._voltage = None

        # Names of the buses coupled to this bus
        self._coupled_bus_names = {self.name}

    def __repr__(self):
        """
        Representation of a bus.
        """
        generators = ")(".join([repr(gen) for gen in self.generators])
        loads = ")(".join([repr(load) for load in self.loads])
        capacitor_banks = ")(".join([repr(bank) for bank in self.capacitor_banks])
        branches = ")(".join([repr(branch) for branch in self.branches])
        return (
            f"Bus: Name=[{self.name}] Type=[{self.type.name}] |Vb|=[{self.base_voltage}] "
            f"|V|=[{self.voltage_magnitude}] \u03C6=[{self.phase_angle}] Generators=[({generators})] "
            f"Loads=[({loads})] Capacitor banks=[({capacitor_banks})] Branches=[({branches})]"
        )

    @property
    def coupled_bus_names(self) -> Set[str]:
        """
        Return the set of the names of all the buses coupled to this one.

        return: The set of the bus names.
        """
        return self._coupled_bus_names

    @property
    def voltage(self) -> complex:
        """
        Return the voltage at the bus (phasor).

        :return: A phasor corresponding to the voltage at the bus (per unit).
        :raise: BusVoltageException if the voltage magnitude and/or angle is/are not specified.
        """
        if self._voltage is None:
            if self._voltage_magnitude is None or self._phase_angle is None:
                raise BusVoltageException(self.name)
            self._voltage = cmath.rect(
                self._voltage_magnitude_pu,
                self._phase_angle
            )
        return self._voltage

    def update_voltage(self, voltage_magnitude: float, phase_angle: float):
        """
        Update bus voltage.

        :param voltage_magnitude: New voltage magnitude.
        :param phase_angle: New phase angle.
        """
        self._voltage_magnitude = voltage_magnitude
        self._voltage_magnitude_pu = voltage_magnitude / self.base_voltage
        self._phase_angle = phase_angle
        self._voltage = None
        for generator in self.generators:
            # Update internal voltage of all connected generators
            generator.compute_internal_voltage()
        for load in self.loads:
            # Update admittance of all connected loads
            load.compute_admittance()
        for bank in self.capacitor_banks:
            # Update admittance of all connected capacitor banks
            bank.compute_admittance()

    @property
    def voltage_magnitude(self) -> float:
        """
        Return the voltage magnitude of this bus.

        :return: The voltage magnitude.
        """
        return self._voltage_magnitude

    @property
    def voltage_magnitude_pu(self) -> float:
        """
        Return the voltage magnitude in pu of this bus.

        :return: The voltage magnitude in pu.
        """
        return self._voltage_magnitude_pu

    @property
    def phase_angle(self) -> float:
        """
        Return the phase angle of this bus.

        :return: The phase angle.
        """
        return self._phase_angle

    @property
    def type(self) -> BusType:
        """
        Determine the type of the bus.

        :return: The bus type.
        """
        if self._type is not None:
            # Return specified type
            return self._type
        # By default, bus is of type PQ
        type = BusType.PQ
        for generator in self.generators:
            if generator.type == GeneratorType.SLACK:
                # Bus connected to slack generator
                return BusType.SLACK
            # Check if a generator is regulating
            if generator.type == GeneratorType.PV:
                type = BusType.PV
        return type

    def add_generator(self, generator: Generator):
        """
        Add a generator to this bus.

        :param generator: Generator to add.
        """
        self.generators.append(generator)

    def add_load(self, load: Load):
        """
        Add a load to this bus.

        :param load: Load to add.
        """
        self.loads.append(load)

    def add_capacitor_bank(self, capacitor_bank: CapacitorBank):
        """
        Add a capacitor bank to this bus.

        :param capacitor_bank: Capacitor bank to add.
        """
        self.capacitor_banks.append(capacitor_bank)

    def add_branch(self, branch: Branch):
        """
        Add a branch to this bus.

        :param branch: Branch to add.
        """
        self.branches.append(branch)

    def couple_to_bus(self, bus: 'Bus'):
        """
        Couple a bus to this one.
        A bus of type GENERATOR_INTERNAL_VOLTAGE can not be coupled.
        Elements connected to the two merged buses are updated during the process.

        :param bus: The bus to couple.
        :raise CoupledBusesException if the two buses cannot be coupled.
        """
        if (
            self.type == BusType.GEN_INT_VOLT or bus.type == BusType.GEN_INT_VOLT or
            self.voltage_magnitude is None or self.phase_angle is None or
            bus.voltage_magnitude is None or bus.phase_angle is None
        ):
            # Buses must not model a generator internal voltage and must have a voltage
            raise CoupledBusesException(self.name, bus.name)

        if self._coupled_bus_names.intersection(bus._coupled_bus_names):
            # Bus already coupled to the input bus
            return

        if (
            (bus.voltage_magnitude != self.voltage_magnitude) or
            (bus.phase_angle != self.phase_angle) or
            (bus.base_voltage != self.base_voltage)
        ):
            # Base voltage and voltage must be the same
            raise CoupledBusesException(self.name, bus.name)
        else:
            # Copy voltages and names
            voltage_magnitude = bus.voltage_magnitude
            phase_angle = bus.phase_angle
            self.update_voltage(voltage_magnitude, phase_angle)
            self.base_voltage = bus.base_voltage
            self.name = f"{self.name}_{bus.name}"

        # Add connected elements and check if slack bus
        for branch in bus.branches:
            if branch.first_bus == bus:
                branch.first_bus = self
            else:
                branch.second_bus = self
            self.branches.append(branch)
        for generator in bus.generators:
            generator.bus = self
            self.generators.append(generator)
        for load in bus.loads:
            load.bus = self
            self.loads.append(load)
        for bank in bus.capacitor_banks:
            bank.bus = self
            self.capacitor_banks.append(bank)
        if bus.type == BusType.SLACK or (bus.type == BusType.PV and self.type != BusType.SLACK):
            self._type = bus.type

        # Update coupled bus names
        self._coupled_bus_names = self._coupled_bus_names.union(bus._coupled_bus_names)
