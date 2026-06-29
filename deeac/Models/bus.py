"""
Module for bus.

:module: bus
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.
from __future__ import annotations
import cmath
from typing import Set, TYPE_CHECKING
from deeac.enums import BusType, GeneratorType

if TYPE_CHECKING:
    from deeac.Models.load import Load
    from deeac.Models.capacitor_bank import CapacitorBank
    from deeac.Models.branch import Branch
    from deeac.Models.generator import Generator




class Bus:
    """
    Bus.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar name: name.
    :ivar base_voltage: base voltage.
    :ivar voltage_magnitude: voltage magnitude.
    :ivar phase_angle: phase angle.
    :ivar tpe: tpe.
    """

    def __init__(self,
                 name: str,
                 base_voltage: float,
                 voltage_magnitude: float = 0.0,
                 phase_angle: float = 0.0,
                 tpe: BusType = None):
        """
        Initialize a bus.
        
        :param name: Name of the bus.
        :param base_voltage: Base voltage for per unit conversions. Unit: kV.
        :param voltage_magnitude: Voltage magnitude at the bus.
        :param phase_angle: Phase angle at the bus. Unit: rad.
        :param tpe: Type of the bus. If None, the type is derived from the connected generators.
        """
        self.name = name
        self.branches = set()
        self.generators = set()
        self.loads = set()
        self.capacitor_banks = set()
        self.base_voltage = base_voltage
        self._type = tpe
        self._voltage_magnitude_pu = voltage_magnitude / base_voltage
        self._phase_angle = phase_angle
        self.voltage = cmath.rect(self._voltage_magnitude_pu, self._phase_angle)

        # Names of the buses coupled to this bus
        self._coupled_bus_names = {self.name}

    def __repr__(self):
        """
        repr  .
        
        :return: Return value.
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
        Coupled bus names.
        
        :return: Return value.
        :rtype: Set[str]
        """
        return self._coupled_bus_names

    def update_voltage(self, voltage_magnitude: float, phase_angle: float):
        """
        Update bus voltage.
        
        :param voltage_magnitude: New voltage magnitude.
        :param phase_angle: New phase angle.
        """
        self._voltage_magnitude_pu = voltage_magnitude / self.base_voltage
        self._phase_angle = phase_angle
        self.voltage = cmath.rect(self._voltage_magnitude_pu, self._phase_angle)
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
        return self._voltage_magnitude_pu * self.base_voltage

    @voltage_magnitude.setter
    def voltage_magnitude(self, voltage_magnitude: float):
        """
        Voltage magnitude.
        
        :param voltage_magnitude: voltage magnitude.
        """
        self._voltage_magnitude_pu = voltage_magnitude / self.base_voltage
        self.update_voltage(voltage_magnitude=voltage_magnitude, phase_angle=self._phase_angle)

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

    @phase_angle.setter
    def phase_angle(self, phase_angle: float):
        """
        Phase angle.
        
        :param phase_angle: phase angle.
        """
        self._phase_angle = phase_angle
        self.update_voltage(voltage_magnitude=self.voltage_magnitude, phase_angle=self.phase_angle)

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
        tpe = BusType.PQ
        for generator in self.generators:
            if generator.tpe == GeneratorType.SLACK:
                # Bus connected to slack generator
                return BusType.SLACK
            # Check if a generator is regulating
            if generator.tpe == GeneratorType.PV:
                tpe = BusType.PV
        return tpe

    def add_generator(self, generator: Generator):
        """
        Add a generator to this bus.
        
        :param generator: Generator to add.
        """
        self.generators.add(generator)

    def add_load(self, load: 'Load'):
        """
        Add a load to this bus.
        
        :param load: Load to add.
        """
        self.loads.add(load)

    def add_capacitor_bank(self, capacitor_bank: 'CapacitorBank'):
        """
        Add a capacitor bank to this bus.
        
        :param capacitor_bank: Capacitor bank to add.
        """
        self.capacitor_banks.add(capacitor_bank)

    def add_branch(self, branch: 'Branch'):
        """
        Add a branch to this bus.
        
        :param branch: Branch to add.
        """
        self.branches.add(branch)

    def couple_to_bus(self, bus: 'Bus'):
        """
        Couple a bus to this one.
        A bus of type GENERATOR_INTERNAL_VOLTAGE can not be coupled.
        Elements connected to the two merged buses are updated during the process.
        
        :param bus: The bus to couple.
        :raise CoupledBusesException if the two buses cannot be coupled.
        """
        if (self.type == BusType.GEN_INT_VOLT or bus.type == BusType.GEN_INT_VOLT or
                self.voltage_magnitude_pu is None or self.phase_angle is None or
                bus.voltage_magnitude_pu is None or bus.phase_angle is None):
            # Buses must not model a generator internal voltage and must have a voltage
            raise ValueError(self.name, bus.name)

        if self._coupled_bus_names.intersection(bus._coupled_bus_names):
            # Bus already coupled to the input bus
            return

        if ((bus.voltage_magnitude_pu != self.voltage_magnitude_pu) or
                (bus.phase_angle != self.phase_angle) or
                (bus.base_voltage != self.base_voltage)):
            # Base voltage and voltage must be the same
            raise ValueError(self.name, bus.name)
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
            self.branches.add(branch)

        for generator in bus.generators:
            generator.bus = self
            self.generators.add(generator)

        for load in bus.loads:
            load.bus = self
            self.loads.add(load)

        for bank in bus.capacitor_banks:
            bank.bus = self
            self.capacitor_banks.add(bank)

        if bus.type == BusType.SLACK or (bus.type == BusType.PV and self.type != BusType.SLACK):
            self._type = bus.type

        # Update coupled bus names
        self._coupled_bus_names = self._coupled_bus_names.union(bus._coupled_bus_names)
