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

:module: parsing_lib
"""

import getopt
import json
import os
import sys
from typing import List, Optional, Sequence

from deeac.IO.plan_loader import parse_execution_plan_data
from deeac.IO.plan_models import ExecutionPlan


class EurostagRunConfiguration:
    """
    Run configuration for a Eurostag-based DEEAC execution.
    
    Rationale:
        This class is the explicit input bundle consumed by the Eurostag EEAC
        run path. It groups the three mandatory Eurostag files, the execution
        plan, the fault sequence files, and a few runtime options.
        
        The constructor still exposes some legacy CLI-oriented fields. The
        important relationships are:
        
        * ``ech_file``, ``dta_file``, and ``lf_file`` always go together.

        * Exactly one of ``execution_tree_file`` or ``execution_tree`` should be provided.

        * ``seq_files`` is the preferred programmatic way to provide the faults.

        * ``seq_file`` is only the single-file convenience form of ``seq_files``.

        * ``seq_file_folder`` is only descriptive or UI-oriented metadata. The
          runner executes the files listed in ``seq_files`` or ``seq_file``.

        * ``output_dir`` and ``json_path`` are two alternative output targets.
          When both are ``None``, the run only returns results in memory.

        * ``rewrite`` only matters when ``output_dir`` is not ``None``.
        
        Recommended programmatic usage is to fill ``execution_tree_file`` and
        ``seq_files`` explicitly, leaving ``execution_tree`` and ``seq_file``
        set to ``None``.
        
        Example:
        
        .. code-block:: python
        
            config = EurostagRunConfiguration(
                ech_file=\"case/fech.ech\",
                dta_file=\"case/fdta.dta\",
                lf_file=\"case/fech.lf\",
                execution_tree_file=\"case/branch_1.json\",
                execution_tree=None,
                seq_file=None,
                seq_file_folder=\"case\",
                seq_files=[
                    \"case/fault_a.seq\",
                    \"case/fault_b.seq\",
                ],
                island_threshold=0.0,
                cores=1,
                protection_delay=0.0,
                verbose=False,
                output_dir=None,
                json_path=None,
                rewrite=True,
                warn=True,
            )
    
    :ivar ech_file: Path to the static data file.
    :ivar dta_file: Path to the dynamic data file.
    :ivar lf_file: Path to the load flow file.
    :ivar execution_tree_file: Optional path to the execution plan file. Use
        this when the plan is still stored as JSON on disk.
    :ivar execution_tree: Optional parsed execution plan. Use this instead of
        ``execution_tree_file`` when the plan has already been loaded.
    :ivar seq_file: Optional single sequence file. This is the one-fault
        convenience form of ``seq_files``.
    :ivar seq_file_folder: Optional folder that contains the sequence files.
        This does not replace ``seq_files`` during programmatic construction.
    :ivar seq_files: Sequence files to run. This is the preferred field for
        programmatic usage.
    :ivar island_threshold: Islanding threshold in MW.
    :ivar cores: Number of cores for parallel execution.
    :ivar protection_delay: Protection delay in ms.
    :ivar verbose: Verbose mode flag.
    :ivar output_dir: Optional output directory path for per-fault files.
    :ivar json_path: Optional JSON output path used instead of ``output_dir``.
    :ivar rewrite: Rewrite output flag. Only relevant when writing to an output
        directory.
    :ivar warn: Warning flag for failure handling.
    """

    def __init__(
        self,
        ech_file: str,
        dta_file: str,
        lf_file: str,
        execution_tree_file: Optional[str],
        execution_tree: Optional[ExecutionPlan],
        seq_file: Optional[str],
        seq_file_folder: Optional[str],
        seq_files: Sequence[str],
        island_threshold: float,
        cores: int,
        protection_delay: float,
        verbose: bool,
        output_dir: Optional[str],
        json_path: Optional[str],
        rewrite: bool,
        warn: bool,
    ) -> None:
        """
        Initialize the run configuration.
        
        :param ech_file: Path to the static data file.
        :param dta_file: Path to the dynamic data file.
        :param lf_file: Path to the load flow file.
        :param execution_tree_file: Optional path to the execution plan JSON
            file. Provide this when the plan must still be read from disk.
        :param execution_tree: Optional already parsed execution plan. Provide
            this instead of ``execution_tree_file``.
        :param seq_file: Optional single sequence file. Keep this set to
            ``None`` when ``seq_files`` is used.
        :param seq_file_folder: Optional folder containing the sequence files.
            This is useful as contextual metadata for CLI or GUI usage.
        :param seq_files: Explicit sequence files to execute. This is the
            preferred field for direct Python usage.
        :param island_threshold: Islanding threshold in MW.
        :param cores: Number of cores for parallel execution.
        :param protection_delay: Protection delay in ms.
        :param verbose: Verbose mode flag.
        :param output_dir: Optional output directory path. Use ``None`` to keep
            results in memory only.
        :param json_path: Optional JSON result file path. This is an
            alternative to ``output_dir``.
        :param rewrite: Rewrite output flag. Only relevant when ``output_dir``
            is not ``None``.
        :param warn: Warning flag for failure handling.
        :return: Return value.
        """
        self.ech_file = ech_file
        self.dta_file = dta_file
        self.lf_file = lf_file
        self.execution_tree_file = execution_tree_file
        self.execution_tree = execution_tree
        self.seq_file = seq_file
        self.seq_file_folder = seq_file_folder
        self.seq_files = list(seq_files)
        self.island_threshold = island_threshold
        self.cores = cores
        self.protection_delay = protection_delay
        self.verbose = verbose
        self.output_dir = output_dir
        self.json_path = json_path
        self.rewrite = rewrite
        self.warn = warn


class DynawoRunConfiguration:
    """
    Run configuration for an IIDM + Dynawo execution.

    Rationale:
        This class mirrors the Eurostag run configuration but replaces the
        topology/dynamic inputs with Dynawo case files.

        There are two valid input modes:

        * Preferred mode: provide ``jobs_file`` and leave ``iidm_file``,
          ``dynawo_dyd_file``, and ``dynawo_par_file`` set to ``None``.
          The parser resolves the case files from the Dynawo ``.jobs`` file.

        * Manual mode: provide ``iidm_file``, ``dynawo_dyd_file``, and
          ``dynawo_par_file`` together, with ``jobs_file`` set to ``None``.

        Unlike Eurostag, Dynawo fault events are discovered from the Dynawo
        dynamic files rather than from ``.seq`` files. For that reason this
        configuration does not expose ``seq_file`` or ``seq_files``.

        Example:

        .. code-block:: python

            config = DynawoRunConfiguration(
                jobs_file="case/IEEE14.jobs",
                iidm_file=None,
                dynawo_dyd_file=None,
                dynawo_par_file=None,
                dynawo_dyn_file=None,
                execution_tree_file="case/branch_1.json",
                execution_tree=None,
                island_threshold=0.0,
                cores=1,
                protection_delay=0.0,
                verbose=False,
                output_dir=None,
                json_path=None,
                rewrite=True,
                warn=True,
            )

    :ivar jobs_file: Optional path to the Dynawo ``.jobs`` file. This is the
        preferred case entrypoint.
    :ivar iidm_file: Optional path to the IIDM network file used in manual
        mode.
    :ivar dynawo_dyd_file: Optional path to the Dynawo ``.dyd`` file used in
        manual mode or resolved from ``jobs_file``.
    :ivar dynawo_par_file: Optional path to the Dynawo ``.par`` file used in
        manual mode or resolved from ``jobs_file``.
    :ivar dynawo_dyn_file: Optional legacy Dynawo dynamic event file path.
        The current workflow reads supported events from ``.dyd`` and ``.par``.
    :ivar execution_tree_file: Optional path to the execution plan file.
    :ivar execution_tree: Optional parsed execution plan.
    :ivar island_threshold: Islanding threshold in MW.
    :ivar cores: Number of cores for parallel execution.
    :ivar protection_delay: Protection delay in ms.
    :ivar verbose: Verbose mode flag.
    :ivar output_dir: Optional output directory path.
    :ivar json_path: Optional output JSON path.
    :ivar rewrite: Rewrite output flag. This only matters when
        ``output_dir`` is not ``None``.
    :ivar warn: Warning flag for failure handling.
    :ivar dynawo_dotted_generator_inertia_multiplier: Multiplier applied
        during Dynawo parsing to generators whose IIDM id starts with ``.``.
        Use ``1.0`` to keep the raw Dynawo inertia values.
    """

    def __init__(
        self,
        jobs_file: Optional[str],
        iidm_file: Optional[str],
        dynawo_dyd_file: Optional[str],
        dynawo_par_file: Optional[str],
        dynawo_dyn_file: Optional[str],
        execution_tree_file: Optional[str],
        execution_tree: Optional[ExecutionPlan],
        island_threshold: float,
        cores: int,
        protection_delay: float,
        verbose: bool,
        output_dir: Optional[str],
        json_path: Optional[str],
        rewrite: bool,
        warn: bool,
        dynawo_dotted_generator_inertia_multiplier: float = 1.0,
    ) -> None:
        """
        Initialize the Dynawo run configuration.

        :param jobs_file: Optional path to the Dynawo ``.jobs`` file. Use this
            in the preferred workflow.
        :param iidm_file: Optional path to the IIDM network file. Use this in
            manual mode together with ``dynawo_dyd_file`` and
            ``dynawo_par_file``.
        :param dynawo_dyd_file: Optional path to the Dynawo ``.dyd`` file.
        :param dynawo_par_file: Optional path to the Dynawo ``.par`` file.
        :param dynawo_dyn_file: Optional legacy Dynawo ``.dyn`` file defining
            events.
        :param execution_tree_file: Optional path to the execution plan file.
        :param execution_tree: Optional parsed execution plan.
        :param island_threshold: Islanding threshold in MW.
        :param cores: Number of cores for parallel execution.
        :param protection_delay: Protection delay in ms.
        :param verbose: Verbose mode flag.
        :param output_dir: Optional output directory path.
        :param json_path: Optional output JSON path.
        :param rewrite: Rewrite output flag.
        :param warn: Warning flag for failure handling.
        :param dynawo_dotted_generator_inertia_multiplier: Multiplier applied
            during Dynawo parsing to generators whose IIDM id starts with ``.``.
        :return: Return value.
        """
        self.jobs_file = jobs_file
        self.iidm_file = iidm_file
        self.dynawo_dyd_file = dynawo_dyd_file
        self.dynawo_par_file = dynawo_par_file
        self.dynawo_dyn_file = dynawo_dyn_file
        self.execution_tree_file = execution_tree_file
        self.execution_tree = execution_tree
        self.island_threshold = island_threshold
        self.cores = cores
        self.protection_delay = protection_delay
        self.verbose = verbose
        self.output_dir = output_dir
        self.json_path = json_path
        self.rewrite = rewrite
        self.warn = warn
        self.dynawo_dotted_generator_inertia_multiplier = dynawo_dotted_generator_inertia_multiplier


def _as_bool(value: object, default: bool = False) -> bool:
    """
    Convert a value to a boolean.
    
    :param value: Input value.
    :param default: Default boolean if conversion fails.
    :return: Parsed boolean.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return default


def _default_cores() -> int:
    """
    Return the default number of cores.

    :return: Default core count.
    """
    return os.cpu_count() or 1


def load_global_configuration(config_path: str) -> EurostagRunConfiguration:
    """
    Load a global configuration JSON file.
    
    :param config_path: Path to the JSON configuration file.
    :return: Parsed run configuration.
    """
    base_path = os.path.dirname(config_path)
    try:
        with open(config_path, "r") as handle:
            config = json.load(handle)
    except json.JSONDecodeError:
        raise IOError(f"Failed to parse JSON global configuration file {config_path}")
    if not isinstance(config, dict):
        raise IOError(f"Global configuration file {config_path} must be a JSON object")

    allowed_keys = {
        "ech-file",
        "dta-file",
        "lf-file",
        "seq-file",
        "seq-file-folder",
        "seq-files-folder",
        "execution-tree-file",
        "execution-plan-file",
        "branch",
        "execution-plan",
        "output-dir",
        "json-results",
        "cores",
        "island-threshold",
        "protection-delay",
        "rewrite",
        "verbose",
        "warn",
        "dynawo-post-run-enabled",
        "dynawo-install-dir",
        "dynawo-binary-path",
        "dynawo-timeout-seconds",
        "dynawo-cct-min",
        "dynawo-cct-max",
        "dynawo-include-potentially-stable",
        "dynawo-eeac-statuses",
    }
    unknown_keys = set(config.keys()) - allowed_keys
    if unknown_keys:
        raise ValueError(f"Unknown configuration keys: {', '.join(sorted(unknown_keys))}")

    ech_file = config.get("ech-file")
    dta_file = config.get("dta-file")
    lf_file = config.get("lf-file")
    seq_file = config.get("seq-file")
    seq_file_folder = config.get("seq-file-folder")
    if seq_file_folder is None:
        seq_file_folder = config.get("seq-files-folder")
    execution_plan_data = config.get("branch")
    execution_plan_alt = config.get("execution-plan")
    execution_plan_file = config.get("execution-tree-file")
    execution_plan_file_alt = config.get("execution-plan-file")
    output_dir = config.get("output-dir")
    json_path = config.get("json-results")

    if ech_file is None or dta_file is None or lf_file is None:
        raise ValueError("Global configuration must define ech-file, dta-file, and lf-file.")

    if (seq_file is None) == (seq_file_folder is None):
        raise ValueError("Global configuration must define exactly one of seq-file or seq-file-folder.")

    if execution_plan_data is not None and execution_plan_alt is not None:
        raise ValueError("Global configuration must define only one of branch or execution-plan.")
    if execution_plan_file is not None and execution_plan_file_alt is not None:
        raise ValueError("Global configuration must define only one of execution-tree-file or execution-plan-file.")

    execution_plan_data = execution_plan_data if execution_plan_data is not None else execution_plan_alt
    execution_plan_file = execution_plan_file if execution_plan_file is not None else execution_plan_file_alt

    if (execution_plan_data is None) == (execution_plan_file is None):
        raise ValueError("Global configuration must define exactly one of branch/execution-plan or execution-tree-file.")

    execution_tree = None
    if isinstance(execution_plan_data, dict):
        execution_tree = parse_execution_plan_data(execution_plan_data)

    ech_file = os.path.join(base_path, ech_file) if ech_file else None
    dta_file = os.path.join(base_path, dta_file) if dta_file else None
    lf_file = os.path.join(base_path, lf_file) if lf_file else None
    seq_file = os.path.join(base_path, seq_file) if seq_file else None
    seq_file_folder = os.path.join(base_path, seq_file_folder) if seq_file_folder else None
    execution_tree_file = os.path.join(base_path, execution_plan_file) if execution_plan_file else None
    output_dir = os.path.join(base_path, output_dir) if output_dir else None
    json_path = os.path.join(base_path, json_path) if json_path else None

    cores = int(config.get("cores", _default_cores()))
    island_threshold = float(config.get("island-threshold", 0))
    protection_delay = float(config.get("protection-delay", 0))
    rewrite = _as_bool(config.get("rewrite"), False)
    verbose = _as_bool(config.get("verbose"), False)
    warn = _as_bool(config.get("warn"), False)

    seq_files: List[str] = []
    if seq_file_folder and os.path.isdir(seq_file_folder):
        for file in os.listdir(seq_file_folder):
            if os.path.splitext(file)[1] == ".seq":
                seq_files.append(os.path.join(seq_file_folder, file))
        seq_files.sort()

    return EurostagRunConfiguration(
        ech_file=ech_file,
        dta_file=dta_file,
        lf_file=lf_file,
        execution_tree_file=execution_tree_file,
        execution_tree=execution_tree,
        seq_file=seq_file,
        seq_file_folder=seq_file_folder,
        seq_files=seq_files,
        island_threshold=island_threshold,
        cores=cores,
        protection_delay=protection_delay,
        verbose=verbose,
        output_dir=output_dir,
        json_path=json_path,
        rewrite=rewrite,
        warn=warn,
    )


def load_dynawo_configuration(config_path: str) -> DynawoRunConfiguration:
    """
    Load a global IIDM + Dynawo configuration JSON file.
    
    :param config_path: Path to the JSON configuration file.
    :return: Parsed IIDM run configuration.
    """
    base_path = os.path.dirname(config_path)
    try:
        with open(config_path, "r") as handle:
            config = json.load(handle)
    except json.JSONDecodeError:
        raise IOError(f"Failed to parse JSON global configuration file {config_path}")
    if not isinstance(config, dict):
        raise IOError(f"Global configuration file {config_path} must be a JSON object")

    allowed_keys = {
        "dynawo-jobs-file",
        "jobs-file",
        "iidm-file",
        "dynawo-dyd-file",
        "dynawo-par-file",
        "dynawo-dyn-file",
        "dyn-file",
        "execution-tree-file",
        "execution-plan-file",
        "branch",
        "execution-plan",
        "output-dir",
        "json-results",
        "cores",
        "island-threshold",
        "protection-delay",
        "rewrite",
        "verbose",
        "warn",
        "dynawo-dotted-generator-inertia-multiplier",
    }
    unknown_keys = set(config.keys()) - allowed_keys
    if unknown_keys:
        raise ValueError(f"Unknown configuration keys: {', '.join(sorted(unknown_keys))}")

    jobs_file = config.get("dynawo-jobs-file")
    if jobs_file is None:
        jobs_file = config.get("jobs-file")
    iidm_file = config.get("iidm-file")
    dynawo_dyd_file = config.get("dynawo-dyd-file")
    dynawo_par_file = config.get("dynawo-par-file")
    dynawo_dyn_file = config.get("dynawo-dyn-file")
    if dynawo_dyn_file is None:
        dynawo_dyn_file = config.get("dyn-file")
    execution_plan_data = config.get("branch")
    execution_plan_alt = config.get("execution-plan")
    execution_plan_file = config.get("execution-tree-file")
    execution_plan_file_alt = config.get("execution-plan-file")
    output_dir = config.get("output-dir")
    json_path = config.get("json-results")

    if jobs_file is None and iidm_file is None:
        raise ValueError("Global configuration must define dynawo-jobs-file/jobs-file or iidm-file.")

    if jobs_file is None:
        if (dynawo_dyd_file is None) ^ (dynawo_par_file is None):
            raise ValueError("Global configuration must define both dynawo-dyd-file and dynawo-par-file together.")
        else:
            pass
    else:
        pass

    if execution_plan_data is not None and execution_plan_alt is not None:
        raise ValueError("Global configuration must define only one of branch or execution-plan.")
    if execution_plan_file is not None and execution_plan_file_alt is not None:
        raise ValueError("Global configuration must define only one of execution-tree-file or execution-plan-file.")

    execution_plan_data = execution_plan_data if execution_plan_data is not None else execution_plan_alt
    execution_plan_file = execution_plan_file if execution_plan_file is not None else execution_plan_file_alt

    if (execution_plan_data is None) == (execution_plan_file is None):
        raise ValueError("Global configuration must define exactly one of branch/execution-plan or execution-tree-file.")

    execution_tree = None
    if isinstance(execution_plan_data, dict):
        execution_tree = parse_execution_plan_data(execution_plan_data)

    jobs_file = os.path.join(base_path, jobs_file) if jobs_file else None
    iidm_file = os.path.join(base_path, iidm_file) if iidm_file else None
    dynawo_dyd_file = os.path.join(base_path, dynawo_dyd_file) if dynawo_dyd_file else None
    dynawo_par_file = os.path.join(base_path, dynawo_par_file) if dynawo_par_file else None
    dynawo_dyn_file = os.path.join(base_path, dynawo_dyn_file) if dynawo_dyn_file else None
    execution_tree_file = os.path.join(base_path, execution_plan_file) if execution_plan_file else None
    output_dir = os.path.join(base_path, output_dir) if output_dir else None
    json_path = os.path.join(base_path, json_path) if json_path else None

    cores = int(config.get("cores", _default_cores()))
    island_threshold = float(config.get("island-threshold", 0))
    protection_delay = float(config.get("protection-delay", 0))
    rewrite = _as_bool(config.get("rewrite"), False)
    verbose = _as_bool(config.get("verbose"), False)
    warn = _as_bool(config.get("warn"), False)
    dynawo_dotted_generator_inertia_multiplier = float(
        config.get("dynawo-dotted-generator-inertia-multiplier", 1.0)
    )

    return DynawoRunConfiguration(
        jobs_file=jobs_file,
        iidm_file=iidm_file,
        dynawo_dyd_file=dynawo_dyd_file,
        dynawo_par_file=dynawo_par_file,
        dynawo_dyn_file=dynawo_dyn_file,
        execution_tree_file=execution_tree_file,
        execution_tree=execution_tree,
        island_threshold=island_threshold,
        cores=cores,
        protection_delay=protection_delay,
        verbose=verbose,
        output_dir=output_dir,
        json_path=json_path,
        rewrite=rewrite,
        warn=warn,
        dynawo_dotted_generator_inertia_multiplier=dynawo_dotted_generator_inertia_multiplier,
    )


def print_usage():
    """
    Print usage.
    
    :return: Return value.
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
        f"\t-c, --cores <path>{tab}Number of cores to use for parallelization (defaults to system cores).\n"
        f"\t-r, --rewrite <bool>{tab}rewrite data if output-dir already exists.\n"
        f"\t-v, --verbose{tab}Verbose mode. Display additional results.\n"
        f"\t-g --global-configuration <path>{tab} json file replacing all the arguments above.\n"
        f"{tab}The rewrite and verbose are replaced by booleans true/false or case insensitive strings 'True'/'False'\n"
        f"{tab}You can either specify the 'execution-tree' directly or the path to a json 'execution-tree-file'"
    )


def print_usage_dynawo():
    """
    Print Dynawo usage.
    
    :return: Return value.
    """
    tab = "\t" * 4
    print(
        f"\nUsage:\n"
        f"\tdeeac [arguments] [options]\n\n"
        f"Arguments:\n"
        f"\t--dynawo-jobs-file <path>{tab}Path to the Dynawo .jobs case file.\n"
        f"\t--iidm-file <path>{tab}Path to the IIDM network file.\n"
        f"\t--dynawo-dyd-file <path>{tab}Path to the Dynawo .dyd file.\n"
        f"\t--dynawo-par-file <path>{tab}Path to the Dynawo .par file.\n"
        f"\t--dynawo-dyn-file <path>{tab}Optional path to the Dynawo .dyn events file.\n"
        f"\t--dynawo-dotted-generator-inertia-multiplier <float>{tab}Multiplier applied to Dynawo generators whose IIDM id starts with '.'.\n"
        f"\t-t, --execution-tree-file <path>{tab}Path to a JSON file containing the EEAC plan to execute.\n"
        f"\t-i, --island-threshold <float>{tab}tolerable amount of isolated production in MW in case of islanding.\n"
        f"\t-p, --protection-delay <float>{tab}tolerable delay between the first and last BusShortCircuitEvent in ms.\n"
        f"Options:\n"
        f"\t-o, --output-dir <path>{tab}Path to an output directory where results are outputted, incompatible with -j.\n"
        f"\t-j, --json-results <path>{tab}Path to the JSON file to save the critical cluster, incompatible with -o.\n"
        f"\t-c, --cores <path>{tab}Number of cores to use for parallelization (defaults to system cores).\n"
        f"\t-r, --rewrite <bool>{tab}rewrite data if output-dir already exists.\n"
        f"\t-v, --verbose{tab}Verbose mode. Display additional results.\n"
        f"\t-g --global-configuration <path>{tab} json file replacing all the arguments above.\n"
        f"{tab}The rewrite and verbose are replaced by booleans true/false or case insensitive strings 'True'/'False'\n"
        f"{tab}Use --dynawo-jobs-file for the normal Dynawo workflow, or specify IIDM/DYD/PAR manually.\n"
        f"{tab}You can either specify the 'execution-plan' directly or the path to a json 'execution-tree-file'"
    )


def parse_eurostag_arguments(argv: Sequence[str]) -> EurostagRunConfiguration:
    """
    Parse.
    
    :param argv: argv.
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
    cores = _default_cores()
    island_threshold = 10
    protection_delay = 15
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
        config = load_global_configuration(global_config)
        ech_file = config.ech_file
        dta_file = config.dta_file
        lf_file = config.lf_file
        seq_file = config.seq_file
        seq_file_folder = None
        execution_tree = config.execution_tree
        execution_tree_file = config.execution_tree_file
        output_dir = config.output_dir
        json_path = config.json_path
        cores = config.cores
        island_threshold = config.island_threshold
        protection_delay = config.protection_delay
        rewrite = config.rewrite
        verbose = config.verbose
        warn = config.warn
        seq_file_folder = config.seq_file_folder

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

    seq_files: List[str] = list()
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

    return EurostagRunConfiguration(
        ech_file=ech_file,
        dta_file=dta_file,
        lf_file=lf_file,
        execution_tree_file=execution_tree_file,
        execution_tree=execution_tree,
        seq_file=seq_file,
        seq_file_folder=seq_file_folder,
        seq_files=seq_files,
        island_threshold=island_threshold,
        cores=cores,
        protection_delay=protection_delay,
        verbose=verbose,
        output_dir=output_dir,
        json_path=json_path,
        rewrite=rewrite,
        warn=warn,
    )


def parse_dynawo_arguments(argv: Sequence[str]) -> DynawoRunConfiguration:
    """
    Parse IIDM + Dynawo arguments.
    
    :param argv: argv.
    :return: Dynawo run configuration.
    """
    try:
        opts, _ = getopt.getopt(
            argv,
            "rhvg:t:o:c:j:i:p:w:",
            [
                "help",
                "global-configuration=",
                "dynawo-jobs-file=",
                "iidm-file=",
                "dynawo-dyd-file=",
                "dynawo-par-file=",
                "dynawo-dyn-file=",
                "dynawo-dotted-generator-inertia-multiplier=",
                "execution-tree-file=",
                "output-dir=",
                "cores=",
                "json-results=",
                "island-threshold=",
                "protection-delay=",
                "verbose",
                "rewrite",
                "warn",
            ],
        )
    except getopt.GetoptError as e:
        print(f"Error: {e}")
        print_usage_dynawo()
        sys.exit(2)

    jobs_file = None
    iidm_file = None
    dynawo_dyd_file = None
    dynawo_par_file = None
    dynawo_dyn_file = None
    execution_tree_file = None
    execution_tree = None
    output_dir = None
    json_path = None
    rewrite = False
    verbose = False
    warn = False
    dynawo_dotted_generator_inertia_multiplier = 1.0
    cores = _default_cores()
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
                print_usage_dynawo()
                sys.exit()
            elif opt == "--iidm-file":
                iidm_file = arg
            elif opt == "--dynawo-jobs-file":
                jobs_file = arg
            elif opt == "--dynawo-dyd-file":
                dynawo_dyd_file = arg
            elif opt == "--dynawo-par-file":
                dynawo_par_file = arg
            elif opt == "--dynawo-dyn-file":
                dynawo_dyn_file = arg
            elif opt == "--dynawo-dotted-generator-inertia-multiplier":
                dynawo_dotted_generator_inertia_multiplier = float(arg)
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
        config = load_dynawo_configuration(global_config)
        jobs_file = config.jobs_file
        iidm_file = config.iidm_file
        dynawo_dyd_file = config.dynawo_dyd_file
        dynawo_par_file = config.dynawo_par_file
        dynawo_dyn_file = config.dynawo_dyn_file
        execution_tree = config.execution_tree
        execution_tree_file = config.execution_tree_file
        output_dir = config.output_dir
        json_path = config.json_path
        cores = config.cores
        island_threshold = config.island_threshold
        protection_delay = config.protection_delay
        rewrite = config.rewrite
        verbose = config.verbose
        warn = config.warn
        dynawo_dotted_generator_inertia_multiplier = config.dynawo_dotted_generator_inertia_multiplier

    if warn is True:
        print("WARNING: the warning option is activated, the CCT will not be computed if any candidates cluster fails")

    if json_path is not None and output_dir is not None:
        print("Error: A path towards an output file and output folder can't both be specified")
        print_usage_dynawo()
        exit(2)
    if jobs_file is None:
        if iidm_file is None:
            print("Error: A path to the IIDM file must be specified.")
            print_usage_dynawo()
            exit(2)
        else:
            pass
        if (dynawo_dyd_file is None) ^ (dynawo_par_file is None):
            print("Error: Both Dynawo .dyd and .par files must be specified together.")
            print_usage_dynawo()
            exit(2)
        else:
            pass
    else:
        if not os.path.exists(jobs_file):
            print(f"Error: file {jobs_file} not found")
            exit(2)
        else:
            pass
    if execution_tree is None:
        if execution_tree_file is None:
            print("Error: An execution tree file must be specified.")
            print_usage_dynawo()
            exit(2)
        elif not os.path.exists(execution_tree_file):
            print(f"Error: file {execution_tree_file} not found")
            exit(2)

    if iidm_file is not None and not os.path.exists(iidm_file):
        print(f"Error: file {iidm_file} not found")
        exit(2)
    else:
        pass
    if dynawo_dyd_file is not None and not os.path.exists(dynawo_dyd_file):
        print(f"Error: file {dynawo_dyd_file} not found")
        exit(2)
    if dynawo_par_file is not None and not os.path.exists(dynawo_par_file):
        print(f"Error: file {dynawo_par_file} not found")
        exit(2)
    if dynawo_dyn_file is not None and not os.path.exists(dynawo_dyn_file):
        print(f"Error: file {dynawo_dyn_file} not found")
        exit(2)

    return DynawoRunConfiguration(
        jobs_file=jobs_file,
        iidm_file=iidm_file,
        dynawo_dyd_file=dynawo_dyd_file,
        dynawo_par_file=dynawo_par_file,
        dynawo_dyn_file=dynawo_dyn_file,
        execution_tree_file=execution_tree_file,
        execution_tree=execution_tree,
        island_threshold=island_threshold,
        cores=cores,
        protection_delay=protection_delay,
        verbose=verbose,
        output_dir=output_dir,
        json_path=json_path,
        rewrite=rewrite,
        warn=warn,
        dynawo_dotted_generator_inertia_multiplier=dynawo_dotted_generator_inertia_multiplier,
    )
