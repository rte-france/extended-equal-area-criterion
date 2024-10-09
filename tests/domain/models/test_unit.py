# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest
import numpy as np

from deeac.domain.models.unit import Unit, UnitType, conversion_factor
from deeac.domain.exceptions import UnitTypeException


class TestUnit:

    def test_unit_type(self):
        assert Unit.S.type == UnitType.CONDUCTANCE
        assert Unit.OHM.type == UnitType.RESISTANCE
        assert Unit.MV.type == UnitType.VOLTAGE
        assert Unit.A.type == UnitType.CURRENT
        assert Unit.MW.type == UnitType.ACTIVE_POWER
        assert Unit.VA.type == UnitType.APPARENT_POWER
        assert Unit.KVAR.type == UnitType.REACTIVE_POWER
        assert Unit.DEG.type == UnitType.ANGLE
        assert Unit.PU.type == UnitType.PER_UNIT

    def test_conversion_factor(self):
        assert conversion_factor(Unit.KV, Unit.V) == 1000
        assert conversion_factor(Unit.VAR, Unit.MVAR) == 1e-6
        assert conversion_factor(Unit.KVA, Unit.MVA) == 0.001
        assert conversion_factor(Unit.MW, Unit.MW) == 1
        assert conversion_factor(Unit.DEG, Unit.RAD) == np.pi / 180
        with pytest.raises(UnitTypeException):
            assert conversion_factor(Unit.KV, Unit.A)
