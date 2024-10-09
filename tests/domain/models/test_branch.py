# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import cmath


class TestBranch:

    def test_repr(self, simple_branch):
        assert repr(simple_branch) == (
            "Branch between nodes BUS1 and BUS2: (A:Line: R=[300 ohm [Base: 100 ohm]] X=[1000 ohm [Base: 100 ohm]] "
            "Gs=[40 S [Base: 10 S]] Bs=[20 S [Base: 10 S]] Closed at first bus=[True] Closed at second bus=[True] "
            "Metal short circuit=[False])(B:Line: R=[100 ohm [Base: 100 ohm]] "
            "X=[2000 ohm [Base: 100 ohm]] Gs=[10 S [Base: 10 S]] Bs=[30 S [Base: 10 S]] Closed at first bus=[True] "
            "Closed at second bus=[True] Metal short circuit=[False])"
            "(C:Line: R=[100 ohm [Base: 100 ohm]] X=[2000 ohm [Base: 100 ohm]] Gs=[10 S [Base: 10 S]] Bs=[30 S "
            "[Base: 10 S]] Closed at first bus=[False] Closed at second bus=[True] Metal short circuit=[False])"
            "(D:Transformer: R=[300 ohm [Base: 100 ohm]] X=[1000 ohm [Base: 100 ohm]] "
            "phase shift angle=[10 deg] Closed at primary=[True] Closed at secondary=[True])"
        )

    def test_get_item(self, simple_branch, simple_line):
        assert simple_branch["A"] == simple_line

    def test_set_item(self, simple_branch, simple_line):
        # Get line at index B for backup
        b_line = simple_branch["B"]
        assert b_line != simple_line
        simple_branch["B"] = simple_line
        assert simple_branch["B"] == simple_line
        # Reset branch to its original state
        simple_branch["B"] = b_line

    def test_admittance(self, simple_branch):
        assert cmath.isclose(simple_branch.admittance, 0.05753963714566794 - 0.2333615502528083j, abs_tol=10e-9)

    def test_shunt_admittance(self, simple_branch):
        assert simple_branch.shunt_admittance == 5.01 + 4.99j

    def test_closed(self, simple_branch):
        assert simple_branch.closed
        simple_branch["A"].closed_at_first_bus = False
        assert simple_branch.closed
        simple_branch["B"].closed_at_first_bus = False
        assert simple_branch.closed
        simple_branch["D"].closed_at_second_bus = False
        assert not simple_branch.closed
        simple_branch["A"].closed_at_first_bus = True
        simple_branch["B"].closed_at_first_bus = True
        simple_branch["D"].closed_at_second_bus = True
