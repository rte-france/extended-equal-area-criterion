# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from .event_data import EventData


class LineShortCircuitClearingEvent(EventData):
    """
    Data of a line short circuit clearing event.
    """
    time: float
    sending_node: str
    receiving_node: str
    parallel_index: str
