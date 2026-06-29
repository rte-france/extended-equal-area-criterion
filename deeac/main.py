"""
Module for __main__.

:module: __main__
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List, Union
import sys

from deeac.GUI import run_gui
from deeac.IO.arguments_parser import (EurostagRunConfiguration, DynawoRunConfiguration,
                                       parse_dynawo_arguments, parse_eurostag_arguments)
from deeac.Models.events.fault_events import FaultEvents
from deeac.Models.network import Network, NetworkComputed
from deeac.Simulations.results import EEACResults
from deeac.deeac_all_paths import apply_events_to_network as apply_events_to_network_impl, deeac_run


def deeac_eurostag(config: EurostagRunConfiguration) -> EEACResults:
    """
    Eurostag entry point of DEEAC.
    
    :param config: Eurostag run configuration.
    :return: EEAC results.
    """
    return deeac_run(config)


def deeac_dynawo(config: DynawoRunConfiguration) -> EEACResults:
    """
    Dynawo entry point of DEEAC.
    
    :param config: Dynawo run configuration.
    :return: EEAC results.
    """
    return deeac_run(config)


def apply_events_to_network(network: Network, computed: NetworkComputed, fault_events: FaultEvents) -> None:
    """
    Apply fault events to a network.
    
    This compatibility wrapper keeps the historical import path used by the
    legacy test suite while delegating the implementation to the shared run
    module.
    
    :param network: Network receiving the events.
    :param computed: Computed network data container.
    :param fault_events: Failure and mitigation events to apply.
    :return: Return value.
    """
    apply_events_to_network_impl(network, computed, fault_events)


def deeac(argv: List[Union[str, int, float]]) -> EEACResults:
    """
    Main entry point of DEEAC.
    :param argv: list of arguments
    -e, --ech-file <path>: Path to the file with static data.
    -d, --dta-file <path>: Path to the file with dynamic data.
    -l, --lf-file <path>: Path to the load flow file.
    -s, --seq-file <path>: Path to the sequence file.
    -f, --seq-file-folder <path>: Path to the folder containing the sequence files.
    -t, --execution-tree-file <path>: Path to a JSON file containing the EEAC tree to execute.
    -o, --output-dir <path>: Path to an output directory where results are outputted, incompatible with -j.
    -j, --json-results <path>: Path to the JSON file to save the critical results, incompatible with -o.
    -c, --cores <path>: number of cores to use for parallelization (1 by default).
    -i, --island-threshold <float>: tolerable amount of isolated production in MW in case of islanding.
    -p, --protection-delay <float>: tolerable delay between the first and last BusShortCircuitEvent.\n"
    -r, --rewrite: rewrite data if output-dir already exists.
    -v, --verbose: Verbose mode. Display additional results.
    -g --global-configuration <path>: json file replacing all the arguments above
    -h, --help: Display help on the standard output.
    -w, --warn: warning if there's a failing critical cluster candidate
    """
    config = parse_eurostag_arguments(argv)

    return deeac_eurostag(config)


def deeac_dynawo_from_args(argv: List[Union[str, int, float]]) -> EEACResults:
    """
    Entry point for IIDM + Dynawo runs using CLI-style arguments.
    
    :param argv: list of arguments.
    :return: EEAC results.
    """
    config = parse_dynawo_arguments(argv)
    return deeac_dynawo(config)


def run() -> None:
    """
    Console entry point for the deeac command.

    :return: Return value.
    """
    args = sys.argv[1:]

    if len(args) > 0:
        deeac(args)
    else:
        run_gui()


if __name__ == "__main__":
    # Examples
    # path = os.path.abspath(os.path.join(os.getcwd(), '..', 'examples', 'eurostag_cases', 'case_4---pst'))
    # sys.argv = ["python",
    #             "-e",
    #             os.path.join(path, "fech.ech"),
    #             "-d",
    #             os.path.join(path, "fdta.dta"),
    #             "-l",
    #             os.path.join(path, "fech.lf"),
    #             "-s",
    #             os.path.join(path, "B-C_fault.seq"),
    #             "-t",
    #             os.path.join(path, "branch_1.json"),
    #             "-o",
    #             os.path.join(path, "testing_results"),
    #             "-v"]
    # sys.argv = ["python",
    #             "-g",
    #             "C:\\Users\\eroot\\Github\\RTE-equal-area-criterion-testing\\docs\\EEAC_Example_RTE_data\\branch_1_all_included.json",]

    run()
