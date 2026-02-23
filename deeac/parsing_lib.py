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
import argparse


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
        f"\t--rm, --ren-model <str>{tab}type of model used for REN generators.\n"
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

    parser = argparse.ArgumentParser(
        prog="deeac",
        add_help=False
    )

    # Help manuel
    parser.add_argument("-h", "--help", action="store_true")

    # Arguments files
    parser.add_argument("-e", "--ech-file")
    parser.add_argument("-d", "--dta-file")
    parser.add_argument("-l", "--lf-file")
    parser.add_argument("-s", "--seq-file")
    parser.add_argument("-f", "--seq-file-folder")
    parser.add_argument("-t", "--execution-tree-file")
    parser.add_argument("-o", "--output-dir")
    parser.add_argument("-j", "--json-results")

    # Numerical parameters
    parser.add_argument("-c", "--cores", type=int, default=1)
    parser.add_argument("-i", "--island-threshold", type=float, default=0)
    parser.add_argument("-p", "--protection-delay", type=float, default=0)

    # Flags
    parser.add_argument("-r", "--rewrite", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-w", "--warn", action="store_true")

    # Others
    parser.add_argument("--rm", "--ren-model", dest = "ren_model", default="load")
    parser.add_argument("-g", "--global-configuration")

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        print_usage()
        sys.exit(2)

    # Explicit Help
    if args.help:
        print_usage()
        sys.exit(0)

    # -----------------------
    # PRIORITY TO GLOBAL FILE
    # -----------------------

    if args.global_configuration:

        if len(argv) > 2:
            print("WARNING: multiple arguments specified, only the global configuration file will be used")

        try:
            with open(args.global_configuration, "r") as f:
                config = json.load(f)
        except json.JSONDecodeError:
            print(f"Failed to parse JSON global configuration file {args.global_configuration}")
            sys.exit(2)

        def get_key(*names):
            for name in names:
                if name in config:
                    return config[name]
            return None

        ech_file = get_key("ech", "ech-file")
        dta_file = get_key("dta", "dta-file")
        lf_file = get_key("lf", "lf-file")
        seq_file = get_key("seq", "seq-file")
        seq_file_folder = get_key("seqs", "seq-files-folder")
        execution_tree = get_key("tree", "execution-tree", "branch")
        execution_tree_file = get_key("tree-file", "execution-tree-file")
        output_dir = get_key("output-dir")
        json_path = get_key("json-results")
        cores = get_key("cores") or 1
        island_threshold = get_key("island-threshold") or 0
        protection_delay = get_key("protection-delay") or 0
        rewrite = bool(get_key("rewrite") or False)
        verbose = bool(get_key("verbose") or False)
        warn = bool(get_key("warn") or False)
        ren_model = get_key("ren-model") or "load"

    else:
        ech_file = args.ech_file
        dta_file = args.dta_file
        lf_file = args.lf_file
        seq_file = args.seq_file
        seq_file_folder = args.seq_file_folder
        execution_tree_file = args.execution_tree_file
        execution_tree = None
        output_dir = args.output_dir
        json_path = args.json_results
        cores = args.cores
        island_threshold = args.island_threshold
        protection_delay = args.protection_delay
        rewrite = args.rewrite
        verbose = args.verbose
        warn = args.warn
        ren_model = args.ren_model

    # -----------
    # VALIDATIONS
    # -----------

    if warn:
        print("WARNING: the warning option is activated, the CCT will not be computed if any candidates cluster fails")

    if json_path and output_dir:
        print("Error: A path towards an output file and output folder can't both be specified")
        print_usage()
        sys.exit(2)

    if ech_file is None or dta_file is None:
        print("Error: A path to the static and dynamic data must be specified.")
        print_usage()
        sys.exit(2)

    if lf_file is None:
        print("Error: A path to the load flow results must be specified.")
        print_usage()
        sys.exit(2)

    if not ((seq_file is None) ^ (seq_file_folder is None)):
        print("Error: A path to a sequence file must be specified.")
        print_usage()
        sys.exit(2)

    if execution_tree is None:
        if execution_tree_file is None:
            print("Error: An execution tree file must be specified.")
            print_usage()
            sys.exit(2)
        elif not os.path.exists(execution_tree_file):
            print(f"Error: file {execution_tree_file} not found")
            sys.exit(2)

    for input_file in (ech_file, dta_file, lf_file):
        if not os.path.exists(input_file):
            print(f"Error: file {input_file} not found")
            sys.exit(2)

    # --------
    # SEQUENCE
    # --------

    seq_files = []

    if seq_file:
        if not os.path.exists(seq_file):
            print(f"Error: file {seq_file} not found")
            sys.exit(2)
    else:
        if not os.path.isdir(seq_file_folder):
            print(f"Error: folder {seq_file_folder} not found")
            sys.exit(2)

        for file in os.listdir(seq_file_folder):
            if os.path.splitext(file)[1] == ".seq":
                seq_files.append(os.path.join(seq_file_folder, file))

    if len(seq_files) == 1:
        seq_file = seq_files[0]

    seq_files.sort()

    # Execute tree if necessary
    if execution_tree is None and execution_tree_file:
        with open(execution_tree_file) as f:
            execution_tree = json.load(f)

    return (
        ech_file,
        dta_file,
        lf_file,
        execution_tree_file,
        execution_tree,
        seq_file,
        seq_files,
        island_threshold,
        cores,
        protection_delay,
        verbose,
        output_dir,
        json_path,
        rewrite,
        ren_model,
        warn,
    )
