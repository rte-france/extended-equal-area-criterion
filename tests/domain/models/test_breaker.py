# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.domain.models import Breaker


class TestBreaker:

    def test_repr(self):
        assert repr(Breaker(True)) == "Breaker: Closed=[True]"


class TestParallelBreakers:

    def test_repr(self, simple_parallel_breakers):
        assert repr(simple_parallel_breakers) == (
            "Parallel breakers: Bus1=[BUS] Bus2=[BUS2] Breakers=[1:CLOSED|2:OPENED]"
        )

    def test_get_item(self, simple_parallel_breakers):
        assert simple_parallel_breakers["1"].closed

    def test_set_item(self, simple_parallel_breakers):
        assert simple_parallel_breakers["1"].closed
        simple_parallel_breakers["1"].closed = False
        assert not simple_parallel_breakers["1"].closed
        simple_parallel_breakers["1"].closed = True

    def test_closed(self, simple_parallel_breakers):
        assert simple_parallel_breakers.closed
        simple_parallel_breakers["1"].closed = False
        assert not simple_parallel_breakers.closed
        simple_parallel_breakers["1"].closed = True
