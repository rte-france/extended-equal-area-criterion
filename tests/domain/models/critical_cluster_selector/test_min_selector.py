# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest

from deeac.domain.services.critical_cluster_selector import MinCriticalClusterSelector, CriticalClusterResults
from deeac.domain.exceptions import CriticalClusterSelectorException


class TestMinCriticalClusterSelector:

    def test_select_cluster(self, case1_zoomib):
        results = [
            CriticalClusterResults(
                critical_angle=1,
                critical_time=0.04,
                maximum_angle=2,
                maximum_time=3.1,
                critical_cluster=case1_zoomib.critical_cluster,
                non_critical_cluster=case1_zoomib.non_critical_cluster,
            ),
            CriticalClusterResults(
                critical_angle=0.5,
                critical_time=0.01,
                maximum_angle=4,
                maximum_time=3.4,
                critical_cluster=case1_zoomib.critical_cluster,
                non_critical_cluster=case1_zoomib.non_critical_cluster,
                dynamic_generators=case1_zoomib.critical_cluster.generators.union(
                    case1_zoomib.non_critical_cluster.generators
                )
            )
        ]
        assert MinCriticalClusterSelector.select_cluster(results) == 1

        # Empty list
        with pytest.raises(CriticalClusterSelectorException):
            MinCriticalClusterSelector.select_cluster([])
