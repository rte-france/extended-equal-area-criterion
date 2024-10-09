# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

"""
Library parsing the input arguments of EEAC
"""

import os
import sys
import json
import getopt


def print_usage():
    """
    Print the usage on the standard output.
    """
    tab = "\t"*4
    print(
        f"\nUsage:\n"
        f"\tpython -m deeac [arguments] [options]\n\n"
        f"Arguments:\n"
        f"\t-e, --ech-file <path>{tab}Path to the file with static data.\n"
        f"\t-d, --dta-file <path>{tab}Path to the file with dynamic data.\n"
        f"\t-l, --lf-file <path>{tab}Path to the load flow file.\n"
        f"\t-s, --seq-file <path>{tab}Path to the sequence file.\n"
        f"\t-f, --seq-file-path <path>{tab}Path to the folder containing all the sequence files to run.\n"
        f"\t-t, --execution-tree-file <path>{tab}Path to a JSON file containing the EEAC tree to execute.\n"
        f"\t-i, --island-threshold <float>{tab}tolerable amount of isolated production in MW in case of islanding.\n"
        f"\t-p, --protection-delay <float>{tab}tolerable delay between the first and last BusShortCircuitEvent in ms.\n"
        f"Options:\n"
        f"\t-o, --output-dir <path>{tab}Path to an output directory where results are outputted, incompatible with -j.\n"
        f"\t-j, --json-results <path>{tab}Path to the JSON file to save the critical cluster, incompatible with -o.\n"
        f"\t-c, --cores <path>{tab}Number of cores to use for parallelization, 1 by default.\n"
        f"\t-r, --rewrite <bool>{tab}rewrite data if output-dir already exists.\n"
        f"\t-v, --verbose{tab}Verbose mode. Display additional results.\n"
        f"\t-g --global-configuration <path>{tab} json file replacing all the arguments above.\n"
        f"{tab}The rewrite and verbose are replaced by booleans true/false or case insensitive strings 'True'/'False'\n"
        f"{tab}You can either specify the 'execution-tree' directly or the path to a json 'execution-tree-file'"
    )


def parse(argv):
    """
    Parse the input arguments or the global configuration file
    """
    # Get arguments
    try:
        opts, _ = getopt.getopt(
            argv,
            "rhve:d:l:s:f:t:o:c:j:i:g:p:w:",
            [
                "help",
                "ech-file=",
                "dta-file=",
                "lf-file=",
                "seq-file=",
                "seq-file-folder=",
                "execution-tree-file=",
                "output-dir=",
                "cores=",
                "json-results=",
                "island-threshold=",
                "global-configuration="
                "protection-delay=",
                "verbose",
                "rewrite",
                "warn"
            ]
        )
    except getopt.GetoptError as e:
        # Bad arguments
        print(f"Error: {e}")
        print_usage()
        sys.exit(2)

    # Check arguments
    ech_file = None
    dta_file = None
    lf_file = None
    seq_file = None
    seq_file_folder = None
    execution_tree_file = None
    execution_tree = None
    output_dir = None
    json_path = None
    rewrite = False
    verbose = False
    warn = False
    cores = 1
    island_threshold = 0
    protection_delay = 0
    global_config = None
    for opt, arg in opts:
        if opt in ("-g", "--global-configuration"):
            if len(opts) > 1:
                print(f"WARNING: {len(opts)} arguments specified, only the global configuration file will be used")
            global_config = arg
            break
    else:
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print_usage()
                sys.exit()
            elif opt in ("-e", "--ech-file"):
                ech_file = arg
            elif opt in ("-d", "--dta-file"):
                dta_file = arg
            elif opt in ("-l", "--lf-file"):
                lf_file = arg
            elif opt in ("-s", "--seq-file"):
                seq_file = arg
            elif opt in ("-f", "--seq-file-folder"):
                seq_file_folder = arg
            elif opt in ("-t", "--execution-tree-file"):
                execution_tree_file = arg
            elif opt in ("-o", "--output-dir"):
                output_dir = arg
            elif opt in ("-c", "--cores"):
                cores = int(arg)
            elif opt in ("-i", "--island-threshold"):
                island_threshold = float(arg)
            elif opt in ("-p", "--protection-delay"):
                protection_delay = float(arg)
            elif opt in ("-j", "--json-results"):
                json_path = arg
            elif opt in ("-v", "--verbose"):
                verbose = True
            elif opt in ("-r", "--rewrite"):
                rewrite = True
            elif opt in ("-w", "--warn"):
                warn = True

    try:
        cores = int(cores)
    except ValueError:
        raise ValueError(f"Number of cores must be an integer: {cores} not allowed")

    if global_config is not None:
        try:
            global_config = json.load(open(global_config, "r"))
        except json.JSONDecodeError:
            raise IOError(f"Failed to parse JSON global configuration file {global_config}")

        try:
            ech_file = global_config["ech"]
        except KeyError:
            ech_file = global_config["ech-file"]

        try:
            dta_file = global_config["dta"]
        except KeyError:
            dta_file = global_config["dta-file"]

        try:
            lf_file = global_config["lf"]
        except KeyError:
            lf_file = global_config["lf-file"]

        try:
            seq_file = global_config["seq"]
        except KeyError:
            try:
                seq_file = global_config["seq-file"]
            except KeyError:
                pass

        try:
            seq_file_folder = global_config["seqs"]
        except KeyError:
            try:
                seq_file_folder = global_config["seq-files-folder"]
            except KeyError:
                pass

        try:
            execution_tree = global_config["tree"]
        except KeyError:
            try:
                execution_tree = global_config["execution-tree"]
            except KeyError:
                try:
                    execution_tree = global_config["branch"]
                except KeyError:
                    pass

        try:
            execution_tree_file = global_config["tree-file"]
        except KeyError:
            try:
                execution_tree_file = global_config["execution-tree-file"]
            except KeyError:
                pass

        try:
            output_dir = global_config["output-dir"]
        except KeyError:
            pass

        try:
            json_path = global_config["json-results"]
        except KeyError:
            pass

        try:
            cores = global_config["cores"]
        except KeyError:
            pass

        try:
            island_threshold = global_config["island-threshold"]
        except KeyError:
            pass

        try:
            protection_delay = global_config["protection-delay"]
        except KeyError:
            pass

        try:
            rewrite = global_config["rewrite"]
            if isinstance(rewrite, str):
                if rewrite.lower() == "true":
                    rewrite = True
                else:
                    rewrite = False
        except KeyError:
            pass

        try:
            verbose = global_config["verbose"]
            if isinstance(verbose, str):
                if verbose.lower() == "true":
                    verbose = True
                else:
                    verbose = False
        except KeyError:
            pass

        try:
            warn = global_config["warn"]
            if isinstance(verbose, str):
                if warn.lower() == "true":
                    warn = True
                else:
                    warn = False
        except KeyError:
            pass

    if warn is True:
        print("WARNING: the warning option is activated, the CCT will not be computed if any candidates cluster fails")

    if json_path is not None and output_dir is not None:
        # There must be either an output folder for everything or simply a path towards the main results
        print("Error: A path towards an output file and output folder can't both be specified")
        print_usage()
        exit(2)
    if ech_file is None or dta_file is None:
        # Input data files must be specified.
        print("Error: A path to the static and dynamic data must be specified.")
        print_usage()
        exit(2)
    if lf_file is None:
        # Load flow file must be specified.
        print("Error: A path to the load flow results must be specified.")
        print_usage()
        exit(2)
    if not ((seq_file is None) ^ (seq_file_folder is None)):
        # Either a sequence file or a folder containing sequence files is needed.
        print("Error: A path to a sequence file must be specified.")
        print_usage()
        exit(2)
    if execution_tree is None:
        if execution_tree_file is None:
            # An execution tree file is needed.
            print("Error: An execution tree file must be specified.")
            print_usage()
            exit(2)
        elif not os.path.exists(execution_tree_file):
            print(f"Error: file {execution_tree_file} not found")
            exit(2)

    # Check that the files specified as input actually exist
    for input_file in (ech_file, dta_file, lf_file):
        if not os.path.exists(input_file):
            print(f"Error: file {input_file} not found")
            exit(2)

    seq_files = list()
    if seq_file is not None and not os.path.exists(seq_file):
        print(f"Error: file {seq_file} not found")
        exit(2)
    elif seq_file is None:
        if not os.path.isdir(seq_file_folder):
            print(f"Error: folder {seq_file_folder} not found")
            exit(2)
        else:
            for file in os.listdir(seq_file_folder):
                if os.path.splitext(file)[1] == ".seq":
                    seq_files.append(os.path.join(seq_file_folder, file))

    if len(seq_files) == 1:
        seq_file = seq_files[0]
    seq_files.sort()

    return ech_file, dta_file, lf_file, execution_tree_file, execution_tree, seq_file, seq_files, \
        island_threshold, cores, protection_delay, verbose, output_dir, json_path, rewrite, warn
