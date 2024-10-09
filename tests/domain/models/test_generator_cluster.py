# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest
import cmath

from deeac.domain.models import GeneratorCluster, DynamicGenerator, NetworkState
from deeac.domain.exceptions import (
    EmptyGeneratorClusterException, GeneratorClusterMemberException, UnknownRotorAngleException
)


class TestGeneratorCluster:

    def test_generators(self, generator_cluster):
        generator_names = {"GENB2", "GENA1", "GENB1", "NHVCEQ"}
        assert {gen.name for gen in generator_cluster.generators} == generator_names
        for generator in generator_cluster.generators:
            assert isinstance(generator, DynamicGenerator)

    def test_total_inertia(self, generator_cluster):
        assert cmath.isclose(generator_cluster.total_inertia, 7774.83, abs_tol=10e-9)

    def test_total_mechanical_power(self, generator_cluster):
        assert cmath.isclose(generator_cluster.total_mechanical_power, 38.475, abs_tol=10e-9)

    def test_contains_generator(self, generator_cluster):
        assert generator_cluster.contains_generator("GENA1")
        assert not generator_cluster.contains_generator("FAKE_GENERATOR")

    def test_partial_center_of_angle(self, generator_cluster):
        assert cmath.isclose(
            generator_cluster.get_partial_center_of_angle(0, NetworkState.DURING_FAULT),
            0.01894242980029327,
            abs_tol=10e-9
        )
        assert cmath.isclose(
            generator_cluster.get_partial_center_of_angle(
                2,
                NetworkState.DURING_FAULT
            ),
            2.927898873673122,
            abs_tol=10e-9
        )
        with pytest.raises(UnknownRotorAngleException):
            generator_cluster.get_partial_center_of_angle(3, NetworkState.DURING_FAULT)
        # Empty cluster
        with pytest.raises(EmptyGeneratorClusterException):
            GeneratorCluster(dynamic_generators=set())

    def test_get_generator_angular_deviation(self, generator_cluster):
        assert cmath.isclose(
            generator_cluster.get_generator_angular_deviation("GENA1", 0, NetworkState.DURING_FAULT),
            0.00347585203271715,
            abs_tol=10e-9
        )
        assert cmath.isclose(
            generator_cluster.get_generator_angular_deviation("GENB1", 2, NetworkState.DURING_FAULT),
            -1.9278988736731222,
            abs_tol=10e-9
        )
        with pytest.raises(UnknownRotorAngleException):
            generator_cluster.get_generator_angular_deviation("GENA1", 3, NetworkState.DURING_FAULT)
        with pytest.raises(GeneratorClusterMemberException):
            generator_cluster.get_generator_angular_deviation("FAKE_GENERATOR", 2, NetworkState.DURING_FAULT)
