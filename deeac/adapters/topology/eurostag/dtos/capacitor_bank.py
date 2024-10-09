# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from pydantic import NonNegativeInt

from .network_data import NetworkData


class CapacitorBank(NetworkData):
    """
    Data of a capacitor bank.
    """
    name: str
    bus_name: str
    number_active_steps: NonNegativeInt
    active_loss_on_step: float
    reactive_power_on_step: float
