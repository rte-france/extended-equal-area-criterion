# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import math
from .unit import Unit, conversion_factor, UNIT_MAPPING
from deeac.domain.exceptions import (
    UnitTypeException, UnitBaseException, PerUnitException, UnknownUnitException, ValueAddBaseException,
    UnitScaleException
)
import deeac.domain.ports.dtos as dtos


class PUBase:
    """
    Base used to perform per-unit conversions.

    :param value: Value of the base.
    :param unit: Unit associated to the value stored for the base.
    """
    def __init__(self, value: float, unit: Unit):
        """
        Initialize the base.

        :param value: Base value.
        :param unit: Base unit.
        :raise UnitBaseException if the value is 0.
        """
        if value == 0:
            raise UnitBaseException()
        self.value = value
        self.unit = unit

    def __eq__(self, other: 'PUBase') -> bool:
        """
        Comparison operator.

        :param other: Other base to compared this one to.
        :return: True if the two bases are identical.
        """
        if other is None:
            return False
        return True if Value(value=self.value, unit=self.unit) == Value(value=other.value, unit=other.unit) else False

    def __repr__(self):
        """
        Representation of a base.
        """
        return f"{self.value} {self.unit.value}"


class Value:
    """
    Representation of a value, with its unit.
    The value may also be converted and stored in per-unit if a base is specified.
    """

    def __init__(self, value: float, unit: Unit, base: PUBase = None):
        """
        Initialize a value.

        :param value: Value to store.
        :param unit: Unit associated to the stored value.
        :param base: Base to allow per-unit conversions of this value.
        :raise UnitTypeException if a base is specified and does not have the same unit type as the value.
        """
        self._value = value
        self._unit = unit
        self._base = base
        self._per_unit = None
        if unit == Unit.PU:
            # Base must be set for per-unit values
            if base is None:
                raise UnitBaseException()
            self._per_unit = self._value
        elif base is not None and unit.type != base.unit.type:
            # Base unit and value unit should be of the same type
            raise UnitTypeException(self._unit.name, base.unit.name)

    def __repr__(self):
        """
        Representation of a value.
        """
        base = ""
        if self._base is not None:
            base = f" [Base: {self._base}]"
        return f"{self._value} {self._unit.value}{base}"

    def __eq__(self, other: 'Value') -> bool:
        """
        Compare two values.

        :param other: Other value to compare this one against.
        """
        if other is None:
            return False
        try:
            return math.isclose(self.value, other.to_unit(self.unit), abs_tol=10e-9) and self.base == other.base
        except (PerUnitException, UnitTypeException, UnitScaleException):
            return False

    def __add__(self, other: 'Value') -> 'Value':
        """
        Add operator.
        Two values can be added in one of these cases:
            Case 1: They have the same base
            Case 2: They do not have a base and have the same unit type
            Case 3: This value has a base, and not the other
            Case 4: This value has no base, but the other does
        The result will have :
            Case 1: The same base, and the same unit as this Value
            Case 2: No base and the same unit as this Value
            Case 3: The base of this Value, and the unit of this Value.
            Case 4: The base of the other Value, and the unit of this Value

        :param other: Other value to add to this one.
        :return: A Value being the sum of this value with the input value.
        :raise UnitTypeException if the two values do not have the same unit type.
        :raise ValueAddBaseException if the two values do not have the same base.
        """
        # Check unit type
        unit_type = self._base.unit.type if self._base is not None else self._unit.type
        other_unit_type = other._base.unit.type if other._base is not None else other._unit.type
        if unit_type != other_unit_type:
            # Units not of the same type
            raise UnitTypeException(unit_type, other_unit_type)

        # Get base
        base = None
        if self._base is None:
            if other._base is not None:
                # Keep unique base
                base = PUBase(other._base.value, other._base.unit)
        else:
            if other._base is None:
                # Keep unique base
                base = PUBase(self._base.value, self._base.unit)
            elif other._base != self._base:
                # Bases are not identical
                raise ValueAddBaseException(self._base, other._base)
            else:
                # Both bases are identical
                base = PUBase(self._base.value, self._base.unit)

        # Result will be in the same unit as this value, except if in per-unit and other value does not have a base.
        unit = self.unit
        if unit == Unit.PU and other._base is None:
            # Convert this value into other unit, and sum
            sum_value = self.to_unit(other._unit) + other._value
            # Convert sum in per-unit
            value = Value(sum_value, other._unit, base).per_unit
            return Value(value, unit, base)

        # Convert other value in common unit and sum
        other_value = other.to_unit(unit)
        return Value(self._value + other_value, unit, base)

    @classmethod
    def from_dto(cls, dto_value: dtos.Value) -> 'Value':
        """
        Create a Value from a DTO.

        :param dto_value: DTO value to use to create the model.
        :return: The model created based on the DTO.
        :raise: UnknownUnitException if unit from DTO is unknown.
        """
        try:
            return cls(
                value=dto_value.value,
                unit=UNIT_MAPPING[dto_value.unit.value]
            )
        except ValueError:
            raise UnknownUnitException(dto_value.unit.value)

    @property
    def value(self) -> float:
        """
        Getter for value.

        :return: stored value.
        """
        return self._value

    @property
    def unit(self) -> Unit:
        """
        Getter for unit.

        :return: Unit corresponding to the stored value.
        """
        return self._unit

    @property
    def base(self) -> PUBase:
        """
        Getter for per-unit base.

        :return: Base for per-unit conversions.
        """
        return self._base

    @base.setter
    def base(self, base: PUBase):
        """
        Setter for per-unit base.

        :param base: New base for per-unit conversions.
        """
        if self._unit != Unit.PU and base.unit.type != self._unit.type:
            # Current unit and new base are not of the same type
            raise UnitTypeException(self._unit.name, base.unit.name)

        if self._base is None:
            # No existing base
            self._base = base
            return
        elif self._base == base:
            # Same base
            return
        elif self._base.unit.type != base.unit.type:
            # Base unit and value unit should be of the same type
            raise UnitTypeException(self._unit.name, base.unit.name)

        # Reset per-unit value
        self._per_unit = None

        if self._unit == Unit.PU:
            # Value stored in PU, convert into base unit
            value = self.to_unit(self._base.unit)
            self._value = value
            self._unit = self._base.unit
            self._base = base
            # Convert into per-unit with new base
            value = self.per_unit
            self._value = value
            self._unit = Unit.PU
        else:
            # Other unit than per-unit, store the new base
            self._base = base

    @property
    def per_unit(self) -> float:
        """
        Return the value in per-unit, if a base is specified.

        raise PerUnitException if no base is specified.
        """
        if self._per_unit is not None:
            return self._per_unit

        if self._base is None:
            raise PerUnitException()

        # Convert to per-unit
        conv_fact = conversion_factor(self._unit, self._base.unit)
        self._per_unit = conv_fact * self._value / self._base.value

        return self._per_unit

    def to_unit(self, unit: Unit) -> float:
        """
        Convert the value into another unit.

        :param unit: Unit the value must be converted into.
        :return A float corresponding the value converted into the unit specified as argument.
        :raise PerUnitException if no base is specified.
        :raise UnitTypeException if the unit types are not compatible.
        :raise UnitScaleException if the output unit does not have any associated scale.
        """
        # Unit is same as instance unit
        if unit == self._unit:
            return self._value

        if unit == Unit.PU:
            # Return PU value
            return self.per_unit
        elif self._unit == Unit.PU:
            # Convert from PU
            conv_fact = conversion_factor(self._base.unit, unit)
            return conv_fact * self._value * self._base.value

        # Stay in same unit type
        conv_fact = conversion_factor(self._unit, unit)
        return conv_fact * self._value
