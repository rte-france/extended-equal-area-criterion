"""
Generator snapshot arrays.

:module: generator_snapshot
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List

import numpy as np

from deeac.Models.generator import Generator


class GeneratorSnapshot:
    """
    Generator snapshot arrays.
    
    Rationale:
        This class represents core power-system model data used across parsing,
        EEAC orchestration, and OMIB/EAC simulations. Instances are created from
        input files and then treated as read-only during the analysis pipeline.
    
    :ivar generators: Generator list.
    :ivar name_to_index: Name to index map.
    :ivar bus_names: Bus names per generator.
    :ivar rotor_angles: Rotor angle array (rad).
    :ivar angular_speeds: Angular speed array (p.u.).
    :ivar mechanical_powers: Mechanical power array (p.u.).
    :ivar inertia_coefficients: Inertia coefficient array.
    :ivar internal_voltage_abs: Internal voltage magnitude array.
    """

    def __init__(self, generators: List[Generator]):
        """
        Initialize the snapshot.
        
        :param generators: Generator list.
        :return: Return value.
        """
        self.generators = list(generators)
        self.name_to_index = {gen.name: i for i, gen in enumerate(self.generators)}
        self.bus_names = [gen.bus.name for gen in self.generators]
        self.rotor_angles = np.array([gen.rotor_angle for gen in self.generators], dtype=float)
        self.angular_speeds = np.zeros(len(self.generators), dtype=float)
        self.mechanical_powers = np.array([gen.mechanical_power for gen in self.generators], dtype=float)
        self.inertia_coefficients = np.array([gen.inertia_coefficient for gen in self.generators], dtype=float)
        self.internal_voltage_abs = np.array([abs(gen.internal_voltage) for gen in self.generators], dtype=float)

    def index_of(self, name: str) -> int:
        """
        Return the generator index for a name.
        
        :param name: Generator name.
        :return: Generator index.
        :rtype: int
        """
        return self.name_to_index[name]
