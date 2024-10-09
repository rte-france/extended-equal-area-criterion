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

from deeac.domain.models import NetworkState, DynamicGenerator
from deeac.domain.models.eeac_tree import EEACTreeNodeIOType, CriticalClustersIdentifierNodeInputs
from deeac.domain.exceptions import EEACTreeNodeInputsException


class TestEEAC:

    def test_provide_inputs(self, basic_domib_eeac):
        # Expected input
        generators = basic_domib_eeac._network.get_state(NetworkState.POST_FAULT).generators
        dynamic_generators = {DynamicGenerator(generator) for generator in generators}
        basic_domib_eeac.provide_inputs({EEACTreeNodeIOType.DYNAMIC_GENERATORS: dynamic_generators})
        assert type(basic_domib_eeac._inputs) == CriticalClustersIdentifierNodeInputs
        assert basic_domib_eeac._inputs.dynamic_generators == dynamic_generators
        assert basic_domib_eeac._inputs.output_dir is None
        assert basic_domib_eeac._inputs.network == basic_domib_eeac._network

        # Unexpected input
        with pytest.raises(EEACTreeNodeInputsException):
            basic_domib_eeac.provide_inputs({EEACTreeNodeIOType.CRIT_ANGLE: 4})

    def test_run(self, basic_domib_eeac, basic_eeac):
        # Basic
        # Provide inputs
        generators = basic_eeac._network.get_state(NetworkState.POST_FAULT).generators
        dynamic_generators = {DynamicGenerator(generator) for generator in generators}
        basic_eeac.provide_inputs({EEACTreeNodeIOType.DYNAMIC_GENERATORS: dynamic_generators})

        # Run
        basic_eeac.run()

        # Check results
        results = basic_eeac._execution_tree[2].outputs.cluster_results
        assert cmath.isclose(results.critical_angle, 1.201235818096255, abs_tol=10e-9)
        assert cmath.isclose(results.critical_time, 0.26732036492951583, abs_tol=10e-9)
        assert cmath.isclose(results.maximum_angle, 2.2379613937808864, abs_tol=10e-9)
        assert cmath.isclose(results.maximum_time, 0.5087925117043797, abs_tol=10e-9)
        assert {gen.name for gen in results.critical_cluster.generators} == {"GENA1"}

        # DOMIB
        # Provide inputs
        generators = basic_domib_eeac._network.get_state(NetworkState.POST_FAULT).generators
        dynamic_generators = {DynamicGenerator(generator) for generator in generators}
        basic_domib_eeac.provide_inputs({EEACTreeNodeIOType.DYNAMIC_GENERATORS: dynamic_generators})

        # Run
        basic_domib_eeac.run()

        # Check results
        results = basic_domib_eeac._execution_tree[6].outputs.cluster_results
        assert cmath.isclose(results.critical_angle, 1.2377099203135737, abs_tol=10e-9)
        assert cmath.isclose(results.critical_time, 0.2671118521286033, abs_tol=10e-9)
        assert cmath.isclose(results.maximum_angle, 2.274435495998205, abs_tol=10e-9)
        assert cmath.isclose(results.maximum_time, 0.5026562886281863, abs_tol=10e-9)
        assert {gen.name for gen in results.critical_cluster.generators} == {"GENA1"}
