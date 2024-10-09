# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import cmath


class TestRevisedDOMIB:

    def test_initial_rotor_angle(self, case1_revised_domib):
        assert cmath.isclose(
            case1_revised_domib.initial_rotor_angle,
            -0.14579127376956852,
            abs_tol=10e-9
        )
