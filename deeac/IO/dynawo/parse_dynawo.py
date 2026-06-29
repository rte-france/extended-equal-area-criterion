"""
Module for parse_dynawo.

:module: parse_dynawo
"""
# Copyright (c) 2020-2025, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Optional

from deeac.IO.arguments_parser import DynawoRunConfiguration
from deeac.IO.dynawo.dynawo_parser import DynawoMultiFileParser
from deeac.Models.network import Network


def parse_dynawo(
    jobs_file: Optional[str],
    iidm_file: Optional[str],
    dyd_file: Optional[str],
    par_file: Optional[str],
    dotted_generator_inertia_multiplier: float = 1.0,
) -> Network:
    """
    Parse a Dynawo case into a DEEAC network.

    This function is the Dynawo-side equivalent of
    :func:`deeac.IO.eurostag.parse_eurostag.parse_eurostag`. It hides the
    multi-file Dynawo resolution details behind a single explicit parse step.

    :param jobs_file: Optional Dynawo ``.jobs`` file used as the preferred case
        entrypoint.
    :param iidm_file: Optional IIDM file path used in manual mode.
    :param dyd_file: Optional DYD file path used in manual mode.
    :param par_file: Optional PAR file path used in manual mode.
    :param dotted_generator_inertia_multiplier: Multiplier applied during
        Dynawo parsing to generators whose IIDM id starts with ``.``.
    :return: Parsed network with Dynawo fault events attached.
    """
    parser = DynawoMultiFileParser(
        jobs_file=jobs_file,
        iidm_file=iidm_file,
        dyd_file=dyd_file,
        par_file=par_file,
        dotted_generator_inertia_multiplier=dotted_generator_inertia_multiplier,
    )
    return parser.parse()


def parse_dynawo_configuration(config: DynawoRunConfiguration) -> Network:
    """
    Parse a Dynawo run configuration into a DEEAC network.

    :param config: Dynawo run configuration.
    :return: Parsed network with Dynawo fault events attached.
    """
    return parse_dynawo(
        jobs_file=config.jobs_file,
        iidm_file=config.iidm_file,
        dyd_file=config.dynawo_dyd_file,
        par_file=config.dynawo_par_file,
        dotted_generator_inertia_multiplier=config.dynawo_dotted_generator_inertia_multiplier,
    )
