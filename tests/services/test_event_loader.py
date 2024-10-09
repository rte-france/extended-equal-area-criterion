# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

class TestEventLoader:

    def test_load_events(self, event_loader, failure_events, mitigation_events):
        f_events, m_events = event_loader.load_events()
        for i, event in enumerate(failure_events):
            assert vars(f_events[i]) == vars(event)
        for i, event in enumerate(mitigation_events):
            assert vars(m_events[i]) == vars(event)
