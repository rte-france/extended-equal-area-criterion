# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List, Tuple

from .identifier import ThresholdBasedIdentifier
from deeac.domain.models import DynamicGenerator


class AccelerationCriticalClustersIdentifier(ThresholdBasedIdentifier):
    """
    Identifier of critical clusters of generators based on the initial acceleration criterion.
    """

    def _compute_criterions(self) -> List[Tuple[DynamicGenerator, float]]:
        """
        Compute the criterion for each generator.

        :return: List of tuples (generator, criterion) associating each generator to its criterion.
        """
        # Compute generator accelerations and maximum acceleration
        criterions = []
        for generator in self._generators:
            acceleration = self._get_generator_initial_acceleration(generator)
            criterions.append((generator, acceleration))
        return criterions
