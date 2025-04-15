# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import sys
import json
import os
import shutil
from datetime import datetime
from joblib import Parallel, delayed

from deeac.adapters.load_flow.eurostag import EurostagLoadFlowParser
from deeac.adapters.topology.eurostag import EurostagTopologyParser
from deeac.adapters.eeac_tree.json import JSONTreeParser
from deeac.domain.exceptions import DEEACException
from deeac.services import NetworkLoader, EEACTreeLoader
from deeac.__parallel__ import run_parallel_fault, run_fault_from_args
from .parsing_lib import parse


def deeac(argv):
    """
    Main entry point of DEEAC.

    :param -e, --ech-file <path>: Path to the file with static data.
    :param -d, --dta-file <path>: Path to the file with dynamic data.
    :param -l, --lf-file <path>: Path to the load flow file.
    :param -s, --seq-file <path>: Path to the sequence file.
    :param -f, --seq-file-folder <path>: Path to the folder containing the sequence files.
    :param -t, --execution-tree-file <path>: Path to a JSON file containing the EEAC tree to execute.
    :param -o, --output-dir <path>: Path to an output directory where results are outputted, incompatible with -j.
    :param -j, --json-results <path>: Path to the JSON file to save the critical results, incompatible with -o.
    :param -c, --cores <path>: number of cores to use for parallelization (1 by default).
    :param -i, --island-threshold <float>: tolerable amount of isolated production in MW in case of islanding.
    :param -p, --protection-delay <float>: tolerable delay between the first and last BusShortCircuitEvent.\n"
    :param -r, --rewrite: rewrite data if output-dir already exists.
    :param -v, --verbose: Verbose mode. Display additional results.
    :param -g --global-configuration <path>: json file replacing all the arguments above
    :param -h, --help: Display help on the standard output.
    :param -w, --warn: warning if there's a failing critical cluster candidate
    """

    ech_file, dta_file, lf_file, execution_tree_file, execution_tree, seq_file, seq_files, island_threshold, \
        cores, protection_delay, verbose, output_dir, json_path, rewrite, warn = parse(argv)

    if output_dir is not None:
        # Check if output directory already exists
        if os.path.isdir(output_dir):
            if len(os.listdir(output_dir)) > 0:
                # If rewrite isn't automatic
                if rewrite is False:
                    user_input = input(
                        "Output directory already exists and contains data.\n"
                        "This data will be deleted. Proceed [Y/N]? "
                    ).upper()
                    while user_input != "Y":
                        if user_input == "N":
                            print("Data not deleted. Execution aborted.")
                            sys.exit(0)
                        else:
                            user_input = input("Please type Y for Yes or N for No: ").upper()

                # Delete directory and create a new one
                shutil.rmtree(output_dir, ignore_errors=True)
                os.makedirs(output_dir)
        else:
            # Directory does not exist
            os.makedirs(output_dir)

    # Start monitoring execution time
    start_time = datetime.now()

    try:
        print("Loading execution tree ...")
        tree_loader = EEACTreeLoader(
            tree_parser=JSONTreeParser(execution_tree_file, execution_tree)
        )
        eeac_tree = tree_loader.load_eeac_tree()
        tree_loading_time = datetime.now()
        # Draw tree if output directory available
        if verbose:
            eeac_tree.draw_graph(f"{output_dir}/execution_tree.pdf")

        print("Loading use case ...")
        network_loader = NetworkLoader(
            topology_parser=EurostagTopologyParser(
                ech_file=ech_file,
                dta_file=dta_file
            ),
            load_flow_parser=EurostagLoadFlowParser(
                load_flow_results_file=lf_file
            )
        )
        network = network_loader.load_network()
        if len(network.generators) == 0:
            print("ERROR: EEAC cannot be applied on a network without any generator.")
            sys.exit(-1)

        network_loading_time = datetime.now()

        print("Compute the pre-fault simplified network")
        network.initialize_simplified_network()

        if seq_file is not None:
            print("One seq file specified, no parallelization")
            critical_results = run_parallel_fault(
                seq_file, eeac_tree, output_dir, network, verbose, datetime.now(), network_loading_time,
                tree_loading_time, start_time, False, island_threshold, protection_delay, warn
            )
            critical_results = {critical_results[0]: critical_results[1]}

        else:
            if output_dir is None:
                output_dirs = [None] * len(seq_files)
            # Creating one output directory for each fault
            else:
                output_dirs = [
                    os.path.join(output_dir, os.path.split(seq_file)[1].split(".")[0]) for seq_file in seq_files
                ]
                for output_directory in output_dirs:
                    os.mkdir(output_directory)

            print(f"Running {len(seq_files)} faults in parallel over {cores} cores")
            zipped_data = [
                (
                    seq_file, eeac_tree, output_path, network, verbose, datetime.now(), network_loading_time,
                    tree_loading_time, start_time, parallel, island_threshold, protection_delay, warn
                )
                for seq_file, output_path, parallel in zip(seq_files, output_dirs, [True] * len(seq_files))
            ]
            # Splitting the pool avoids it to crash
            critical_results = dict()
            n_jobs = len(zipped_data)

            # If one core only has been selected run them one by one without processing pool
            if cores == 1:
                for n, data in enumerate(zipped_data):
                    print(f"Running fault {n + 1}/{n_jobs}")
                    result = run_parallel_fault(*data)
                    critical_results[result[0]] = result[1]
            else:
                results = Parallel(n_jobs=cores)(
                    delayed(run_fault_from_args)(data) for data in zipped_data
                )
                for i, result in enumerate(results):
                    critical_results[result[0]] = result[1]

        formatted_critical_results = dict()
        for fault in sorted(critical_results.keys()):
            result = critical_results[fault]
            if isinstance(result, str):
                formatted_critical_results[fault] = {"status": result}
            elif isinstance(result, dict):
                formatted_critical_results[fault] = result
            elif len(result) != 1:
                message = result[0]["warning"]
                if warn is True:
                    formatted_critical_results[fault] = {
                        "status": "COMPUTATION_FAILURE",
                        "failure_report": f"{message}. Failure is global because of --warn option."
                    }
                else:
                    formatted_critical_results[fault] = result[1]
                    formatted_critical_results[fault]["warning"] = message
            else:
                formatted_critical_results[fault] = result[0]

        # Save the results in the output folder if specified under a default name
        if output_dir is not None:
            json_path = os.path.join(output_dir, 'critical_cluster_results.json')

        # Save the critical results at the specified location
        if json_path is not None:
            json.dump(formatted_critical_results, open(json_path, 'w'), indent=2)

        # If neither are specified, don't save
        return formatted_critical_results

    except DEEACException as e:
        print(f"\t* ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    deeac(sys.argv[1:])
