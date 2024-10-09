# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest

from deeac.domain.models.value import Value, PUBase
from deeac.domain.models.unit import Unit
from deeac.domain.exceptions import UnitTypeException, UnitBaseException, PerUnitException, ValueAddBaseException
import deeac.domain.ports.dtos as dtos


class TestBase:

    def test_base(self):
        PUBase(1, Unit.MV)
        with pytest.raises(UnitBaseException):
            PUBase(0, Unit.MV)
        assert PUBase(1, Unit.MV) == PUBase(1000, Unit.KV)
        assert PUBase(1, Unit.MV) != PUBase(1000, Unit.MV)


class TestValue:

    def test_value(self):
        base = PUBase(100, Unit.MVA)

        # Value not in same unit type as base
        with pytest.raises(UnitTypeException):
            Value(34, Unit.A, base)

        # Valid value in same scale as base
        value = Value(34, Unit.MVA, base)
        assert value.value == 34
        assert value.unit == Unit.MVA
        assert value.base == base
        assert value.per_unit == 0.34
        assert value.to_unit(Unit.KVA) == 34000
        assert value.to_unit(Unit.PU) == 0.34
        with pytest.raises(UnitTypeException):
            value.to_unit(Unit.MW)

        # Valid value in different scale than base
        value = Value(34000, Unit.KVA, base)
        assert value.value == 34000
        assert value.unit == Unit.KVA
        assert value.base == base
        assert value.per_unit == 0.34
        assert value.to_unit(Unit.MVA) == 34
        assert value.to_unit(Unit.VA) == 34e6
        assert value.to_unit(Unit.PU) == 0.34

        # Valid value directly in per unit
        value = Value(0.34, Unit.PU, base)
        assert value.value == 0.34
        assert value.unit == Unit.PU
        assert value.base == base
        assert value.per_unit == 0.34
        assert value.to_unit(Unit.PU) == 0.34
        assert value.to_unit(Unit.MVA) == 34
        assert value.to_unit(Unit.KVA) == 34000
        assert value.to_unit(Unit.VA) == 34e6
        with pytest.raises(UnitTypeException):
            value.to_unit(Unit.MW)
        with pytest.raises(UnitBaseException):
            # No base specified
            Value(0.34, Unit.PU)

        # Value without base
        value = Value(34000, Unit.KVA)
        assert value.value == 34000
        assert value.unit == Unit.KVA
        assert value.base is None
        with pytest.raises(PerUnitException):
            value.per_unit
        with pytest.raises(PerUnitException):
            value.to_unit(Unit.PU)
        assert value.to_unit(Unit.MVA) == 34
        assert value.to_unit(Unit.VA) == 34e6

        # Change base with invalid type
        with pytest.raises(UnitTypeException):
            value.base = PUBase(100, Unit.KV)

        # Add new base
        new_base = PUBase(100, Unit.MVA)
        value.base = PUBase(100, Unit.MVA)
        assert value.value == 34000
        assert value.unit == Unit.KVA
        assert value.base == new_base
        assert value.per_unit == 0.34
        assert value.to_unit(Unit.PU) == 0.34
        assert value.to_unit(Unit.MVA) == 34

        # Change with same base
        value = Value(34000, Unit.KVA, base)
        new_base = PUBase(100, Unit.MVA)
        value.base = new_base
        assert value.base == new_base
        assert value.value == 34000
        assert value.unit == Unit.KVA
        assert value.per_unit == 0.34
        assert value.to_unit(Unit.VA) == 34e6

        # Change with new base value
        value.base = PUBase(10, Unit.MVA)
        assert value.value == 34000
        assert value.unit == Unit.KVA
        assert value.per_unit == 3.4
        assert value.to_unit(Unit.VA) == 34e6

        # Change with new base unit
        value.base = PUBase(10, Unit.KVA)
        assert value.value == 34000
        assert value.unit == Unit.KVA
        assert value.per_unit == 3400
        assert value.to_unit(Unit.VA) == 34e6

        # Change PU value base from 100 MVA to 10 KVA
        value = Value(0.34, Unit.PU, base)
        assert value.value == 0.34
        assert value.unit == Unit.PU
        assert value.base == base
        new_base = PUBase(10, Unit.KVA)
        value.base = new_base
        assert value.base == new_base
        assert value.value == 3400
        assert value.unit == Unit.PU
        assert value.to_unit(Unit.VA) == 34e6

        # Change base with invalid type
        with pytest.raises(UnitTypeException):
            value.base = PUBase(100, Unit.KV)

    def test_add_values(self):
        # MVA values with same base
        base1 = PUBase(100, Unit.MVA)
        value1 = Value(34, Unit.MVA, base1)
        value2 = Value(16, Unit.MVA, base1)
        sum_value = value1 + value2
        assert sum_value.base == base1
        assert sum_value.value == 50
        assert sum_value.unit == Unit.MVA

        # MVA values with different bases
        base2 = PUBase(10, Unit.KVA)
        value2 = Value(16, Unit.MVA, base2)
        with pytest.raises(ValueAddBaseException):
            sum_value = value1 + value2

        # Values with different units
        value2 = Value(16000, Unit.KVA, base1)
        sum_value = value1 + value2
        assert sum_value.base == base1
        assert sum_value.value == 50
        assert sum_value.unit == Unit.MVA

        # Incompatible units
        base2 = PUBase(10, Unit.MW)
        value2 = Value(16, Unit.MW, base2)
        with pytest.raises(UnitTypeException):
            value1 + value2

        # Sum in per-unit
        base1 = PUBase(100, Unit.MVA)
        value1 = Value(34, Unit.PU, base1)
        value2 = Value(16, Unit.PU, base1)
        sum_value = value1 + value2
        assert sum_value.base == base1
        assert sum_value.value == 50
        assert sum_value.unit == Unit.PU

        # First in per unit, other not, keep PU
        base1 = PUBase(10, Unit.MVA)
        value1 = Value(34, Unit.PU, base1)
        value2 = Value(16, Unit.MVA, base1)
        sum_value = value1 + value2
        assert sum_value.base == base1
        assert sum_value.value == 35.6
        assert sum_value.unit == Unit.PU

        # Second in per unit, first not, keep MVA
        value1 = Value(16, Unit.MVA, base1)
        value2 = Value(34, Unit.PU, base1)
        sum_value = value1 + value2
        assert sum_value.base == base1
        assert sum_value.value == 356
        assert sum_value.unit == Unit.MVA

        # First in per unit, other has no base
        value1 = Value(16, Unit.PU, base1)
        value2 = Value(34000, Unit.KVA)
        sum_value = value1 + value2
        assert sum_value.base == base1
        assert sum_value.value == 19.4
        assert sum_value.unit == Unit.PU

        # Values with no base
        value1 = Value(16, Unit.MVA)
        value2 = Value(34000, Unit.KVA)
        sum_value = value1 + value2
        assert sum_value.base is None
        assert sum_value.value == 50
        assert sum_value.unit == Unit.MVA

        # First has no base, other in per-unit
        value1 = Value(34000, Unit.KVA)
        value2 = Value(16, Unit.PU, base1)
        sum_value = value1 + value2
        assert sum_value.base == base1
        assert sum_value.value == 194000
        assert sum_value.unit == Unit.KVA

    def test_eq_values(self):
        # Same
        assert Value(34000, Unit.KVA) == Value(34000, Unit.KVA)
        assert Value(34, Unit.MVA) == Value(34000, Unit.KVA)
        base1 = PUBase(value=1000, unit=Unit.VA)
        base2 = PUBase(value=1, unit=Unit.KVA)
        assert Value(34000, Unit.VA, base=base1) == Value(34000, Unit.VA, base=base2)
        # Differ on value
        assert Value(3400, Unit.KVA) != Value(34000, Unit.KVA)
        assert Value(34000, Unit.VA) != Value(34000, Unit.KVA)
        # Differ on base
        base1 = PUBase(value=10, unit=Unit.VA)
        base2 = PUBase(value=20, unit=Unit.VA)
        assert Value(34000, Unit.VA, base=base1) != Value(34000, Unit.KVA, base=base2)
        base1 = PUBase(value=10, unit=Unit.VA)
        base2 = PUBase(value=10, unit=Unit.KVA)
        assert Value(34000, Unit.VA, base=base1) != Value(34000, Unit.KVA, base=base2)
        # Incompatible units
        assert Value(34000, Unit.KVA) != Value(34000, Unit.MW)

    def test_from_dto(self):
        dto_value = dtos.Value(
            value=10,
            unit=dtos.Unit.VA
        )
        v = Value.from_dto(dto_value)
        assert v.value == 10
        assert v.unit == Unit.VA
