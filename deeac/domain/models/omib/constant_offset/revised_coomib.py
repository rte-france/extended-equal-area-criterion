# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from .coomib import COOMIB
from deeac.domain.models.omib import RevisedOMIB


class RevisedCOOMIB(RevisedOMIB, COOMIB):
    """
    Class modeling a revised Constant-Offset One Machine Infinite Bus (COOMIB) system based on two sets of generators.
    A revised COOMIB is similar to a COOMIB, except that the initial angle is computed based on the partial angles of
    both the critical and non-critical sets.
    """
    pass
