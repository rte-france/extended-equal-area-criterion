# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from .zoomib import ZOOMIB
from deeac.domain.models.omib import RevisedOMIB


class RevisedZOOMIB(RevisedOMIB, ZOOMIB):
    """
    Class modeling a revised Zero-Offset One Machine Infinite Bus (ZOOMIB) system based on two sets of generators.
    A revised ZOOMIB is similar to a ZOOMIB, except that the initial angle is computed based on the partial angles of
    both the critical and non-critical sets.
    """
    pass
