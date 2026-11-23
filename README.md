# DEEAC (RTE Equal Area Criterion)

DEEAC runs a fast transient stability analysis based on the Extended Equal Area Criterion (EEAC).
It reads Eurostag network data and fault events, identifies critical generator clusters, builds an
OMIB equivalent, and computes critical clearing times for each fault.

This repository expects **non-public data** (Eurostag cases). Do not publish sample data here.

## Requirements

- Python 3.10 (the supported version for this repository)
- `pypowsybl>=1.13`, installed by the package, for Dynawo/IIDM parsing
- Eurostag inputs:
  - `.ech` (topology)
  - `.dta` (dynamic generator data)
  - `.lf` (load-flow results)
  - `.seq` (fault events, one file or a folder)
- Dynawo inputs:
  - preferred: `.jobs` (Dynawo case entrypoint)
  - manual fallback: `.iidm` + `.dyd` + `.par`
- EEAC execution plan JSON (linear plan)

## Install

Create and use a Python 3.10 virtual environment, then install DEEAC in
editable mode:

```bash
python3.10 -m venv .venv310
.venv310/bin/python -m pip install --upgrade pip
.venv310/bin/python -m pip install -e ".[tests]"
```

Use `.venv310/bin/python` for the examples and tests below. The install also
adds `.venv310/bin/deeac`; omit `.[tests]` when pytest is not needed. Dynawo
itself is only needed to run the generated Dynawo cases; EEAC parsing and case
preparation do not invoke the Dynawo executable.

If `tkinter` is missing, install the system Tk package before running the GUI.
This is especially common when using the system Python on Ubuntu.

Ubuntu / Debian, system Python:

```bash
sudo apt update
sudo apt install python3-tk
```

If you are using a version-specific Python outside the default Ubuntu `python3`,
install the matching Tk package if your distribution provides it, for example:

```bash
sudo apt install python3.12-tk
```

Quick check:

```bash
python3 -c "import tkinter; print(tkinter.TkVersion)"
```

If that import fails, the GUI will not start. The command line and programmatic
APIs do not require `tkinter` unless you actually launch the GUI.

Build a wheel:

```bash
python -m build
```

## Docker operation

The Docker image is meant for the CLI workflow. It packages the `deeac/`
source tree and install metadata, then runs `deeac` as the container entrypoint.

Build the image from the repository root:

```bash
docker build -t deeac .
```

Confirm the container starts and the CLI is available:

```bash
docker run --rm deeac --help
```

Run a Eurostag case by mounting a local case directory into `/work/case`:

```bash
docker run --rm \
  -v "$PWD/examples/eurostag_cases/case_1---basecase:/work/case" \
  deeac \
  -e /work/case/fech.ech \
  -d /work/case/fdta.dta \
  -l /work/case/fech.lf \
  -s /work/case/B-C_fault.seq \
  -t /work/case/branch_1.json \
  -o /work/case/docker_output \
  -r
```

Expected mounted inputs:

- `fech.ech`
- `fdta.dta`
- `fech.lf`
- one or more `.seq` files
- one EEAC execution plan JSON such as `branch_1.json`

The output folder is written inside the mounted directory, so results remain on
the host after the container exits.

You can also run with a global configuration file:

```bash
docker run --rm \
  -v "$PWD/examples/eurostag_cases/case_1---basecase:/work/case" \
  deeac \
  -g /work/case/global_config.json
```

The Docker build context intentionally excludes everything except `setup.py`,
`README.md`, and the `deeac/` source tree.

## Quick start

Run with a global configuration JSON:

```bash
.venv310/bin/deeac -g /path/to/config.json
```

## Eurostag inputs

For a Eurostag run, DEEAC expects four kinds of inputs:

- `fech.ech`: network topology and static electrical data.
- `fdta.dta`: dynamic generator and control-model data.
- `fech.lf`: load-flow results used to initialize the network state.
- one or more `.seq` files: fault and clearing events to evaluate.

In practice, one Eurostag case is usually a folder containing one common
`*.ech`, one common `*.dta`, one common `*.lf`, and many `*.seq` files. DEEAC
loads the common network once, then runs the EEAC pipeline independently for
each sequence file.

Programmatic usage should usually provide the fault files explicitly through
`EurostagRunConfiguration.seq_files`. The older `seq-file` and
`seq-file-folder` ideas exist mostly for CLI and GUI convenience.

## Configuration (global JSON)

Example:

```json
{
  "ech-file": "fech.ech",
  "dta-file": "fdta.dta",
  "lf-file": "fech.lf",
  "seq-file": "B-C_fault.seq",
  "execution-plan-file": "branch_1.json",
  "output-dir": "eeac_output",
  "cores": 1,
  "island-threshold": 0.0,
  "protection-delay": 0.0,
  "rewrite": false,
  "verbose": false,
  "warn": false
}
```

Notes:
- Use exactly one of `seq-file` or `seq-file-folder` (legacy key `seq-files-folder` is accepted).
- Use exactly one of `execution-plan-file` or an inline plan (`branch` or `execution-plan`).
- Paths are resolved relative to the JSON file location.
- `output-dir` writes a default JSON output file; alternatively use `json-results`.

Dynawo example:

```json
{
  "dynawo-jobs-file": "network.jobs",
  "execution-plan-file": "branch_1.json",
  "output-dir": "eeac_output",
  "cores": 1,
  "island-threshold": 0.0,
  "protection-delay": 0.0,
  "rewrite": false,
  "verbose": false,
  "warn": false
}
```

Notes:
- Preferred Dynawo configuration uses `dynawo-jobs-file` or `jobs-file`.
- Manual fallback is still supported through `iidm-file`, `dynawo-dyd-file`, and `dynawo-par-file`.
- Keep the Dynawo base case fault-free during EEAC. Supply fault scenarios as
  separate JSON files to the Dynawo workflow, then generate Dynawo-ready cases
  only for the selected EEAC results.

## CLI options (summary)

- `-e`, `--ech-file` Path to `.ech`.
- `-d`, `--dta-file` Path to `.dta`.
- `-l`, `--lf-file` Path to `.lf`.
- `-s`, `--seq-file` Path to a single `.seq`.
- `-f`, `--seq-file-folder` Path to a folder of `.seq` files.
- `-t`, `--execution-tree-file` Path to the execution plan JSON.
- `-o`, `--output-dir` Output folder for results.
- `-j`, `--json-results` Output JSON path (exclusive with `-o`).
- `-c`, `--cores` Parallel workers.
- `-i`, `--island-threshold` Islanding threshold in MW.
- `-p`, `--protection-delay` Protection delay in ms.
- `-r`, `--rewrite` Overwrite output directory.
- `-v`, `--verbose` Verbose mode.
- `-w`, `--warn` Treat failed candidates as a global warning.
- `-g`, `--global-configuration` Global JSON config.

## Outputs

Results are returned to the caller and optionally written to JSON. Each fault produces a result
with fields like:

- `status`
- `CCT`
- `critical_cluster`
- `swing_state`
- `node_id`
- `warning` / `error_msg`

## Programmatic use

```python
from deeac.main import deeac

results = deeac(["-g", "/path/to/config.json"])
print(results.to_dict())
```

Dynawo parsing (optional):

```python
from deeac.IO.dynawo.parse_dynawo import parse_dynawo

network = parse_dynawo(
    jobs_file="/path/to/network.jobs",
    iidm_file=None,
    dynawo_dyd_file=None,
    dynawo_par_file=None,
)
```

Run EEAC from an external Dynawo fault JSON file (or a folder of JSON files):

```python
from deeac.IO.arguments_parser import DynawoRunConfiguration
from deeac.workflows import run_dynawo_simulation_workflow

config = DynawoRunConfiguration(
    jobs_file="/path/to/IEEE14.jobs",
    iidm_file=None,
    dynawo_dyd_file=None,
    dynawo_par_file=None,
    dynawo_dyn_file=None,
    execution_tree_file="/path/to/branch_1.json",
    execution_tree=None,
    island_threshold=0.0,
    cores=1,
    protection_delay=0.0,
    verbose=False,
    output_dir="/path/to/eeac_output",
    json_path=None,
    rewrite=True,
    warn=False,
)
results, case_directories = run_dynawo_simulation_workflow(
    config=config,
    fault_files="/path/to/faults",
    jobs_file="/path/to/IEEE14.jobs",
    generation_dir="/path/to/generated_dynawo_cases",
)
```

## Operating the new workflows

The normal command-line workflow is Eurostag. The two workflows below are the
new customer-facing paths and are deliberately Python APIs: they keep the
Dynawo source case fault-free while EEAC evaluates independent scenarios.

```mermaid
flowchart LR
    E[Eurostag .ech/.dta/.lf + .seq] --> A[EEAC]
    D[Fault-free Dynawo .jobs case] --> G[Generate selected Dynawo cases]
    A --> G
    G --> C[One runnable case per fault]
```

```mermaid
flowchart LR
    D[Fault-free Dynawo .jobs case] --> A[EEAC]
    F[One fault JSON or folder] --> A
    A --> G[Generate selected Dynawo cases]
    D --> G
    G --> C[One runnable case per fault]
```

### 1. Eurostag EEAC, then Dynawo cases

Use this when the faults already exist as Eurostag `.seq` files. DEEAC runs
EEAC from the Eurostag network, maps the selected line faults to the Dynawo
IIDM case, and creates the Dynawo cases. Do not create a second JSON fault
catalogue for this workflow.

```python
from deeac.IO.arguments_parser import EurostagRunConfiguration
from deeac.workflows import run_eurostag_to_dynawo_workflow

config = EurostagRunConfiguration(
    ech_file="case/fech.ech", dta_file="case/fdta.dta", lf_file="case/fech.lf",
    execution_tree_file="case/branch_1.json", execution_tree=None,
    seq_file=None, seq_file_folder="case/faults",
    seq_files=["case/faults/fault_1.seq", "case/faults/fault_2.seq"],
    island_threshold=0.0, cores=1, protection_delay=0.0, verbose=False,
    output_dir="eeac_results", json_path=None, rewrite=True, warn=False,
)
results, generated_cases = run_eurostag_to_dynawo_workflow(
    config=config,
    dynawo_jobs_file="dynawo/IEEE14_JOBS.xml",
    generation_dir="generated_dynawo_cases",
)
```

Pass `selected_fault_ids=[...]` to generate only selected EEAC results. With
the default settings, every selected fault gets an independent copied Dynawo
case folder.

### 2. Dynawo EEAC from external fault JSON

Use this when the network comes from Dynawo and the scenarios are supplied as
separate JSON files. `fault_files` accepts one JSON file, a directory of JSON
files, or an explicit list. Every JSON file is one scenario. The base IIDM,
DYD, PAR, and JOBS files are read during EEAC and are not modified.

```python
from deeac.IO.arguments_parser import DynawoRunConfiguration
from deeac.workflows import run_dynawo_simulation_workflow

config = DynawoRunConfiguration(
    jobs_file="dynawo/IEEE14_JOBS.xml", iidm_file=None,
    dynawo_dyd_file=None, dynawo_par_file=None, dynawo_dyn_file=None,
    execution_tree_file="case/branch_1.json", execution_tree=None,
    island_threshold=0.0, cores=1, protection_delay=0.0, verbose=False,
    output_dir="eeac_results", json_path=None, rewrite=True, warn=False,
)
results, generated_cases = run_dynawo_simulation_workflow(
    config=config,
    fault_files="faults",
    jobs_file="dynawo/IEEE14_JOBS.xml",
    generation_dir="generated_dynawo_cases",
)
```

The generation directory must be outside the source Dynawo case directory.
`selected_fault_ids=None` generates all analyzed faults; pass a list to select
only those IDs.

### Fault JSON

This is a complete line-fault example. `static_id` and terminal IDs are used
when generating Dynawo files; the bus names and parallel ID are used by EEAC.

```json
{
  "fault_id": "line_1_2",
  "fault_type": "line",
  "target": {
    "first_bus": "BUS_1", "second_bus": "BUS_2", "parallel_id": "1",
    "static_id": "LINE_1_2", "terminal_1": "BUS_1_TN", "terminal_2": "BUS_2_TN"
  },
  "impedance": {"r": 0.0, "x": 0.0},
  "start_time": 1.0,
  "end_time": 1.1,
  "distance": 0.5,
  "disconnection_time": 1.1
}
```

For a line fault, `distance` is strictly between 0 and 1 and EEAC currently
requires zero impedance. A node or transformer fault uses `fault_type` `node`
or `transformer` and a target with `bus`, `static_id`, and `terminal_1`.
Transformer targets additionally use `transformer_id`. Use either a common
`disconnection_time`, which derives the trips from IIDM topology, or an
explicit `disconnections` list. Explicit extra trips need `static_id` and
`time`; line trips also need `first_bus`, `second_bus`, and `parallel_id` for
EEAC.

### Generated Dynawo cases

The default is one copied source-case folder per selected scenario, with a
patched DYD/PAR pair and, when required, IIDM. Line, node, and transformer
faults are supported. Set `line_fault_model_available=False` when the target
Dynawo installation has no `LineFault`: DEEAC splits the copied IIDM line at
the fault point and writes a `NodeFault` at the fictitious bus. Set
`use_multiple_jobs=True` only for a Dynawo setup that supports `.multiple`;
it produces one copied base case with a DYD/PAR pair per scenario and a
dispatcher file. Multiple fallback faults on the same original line are not
supported in that mode.

IIDM node-breaker networks are parsed through their busbar sections, so the
same Dynawo workflow also accepts node-breaker cases. The fault target must
use the EEAC busbar-section name resolved from that IIDM network.

## Verification

Run the focused workflow and node-breaker checks with:

```bash
.venv310/bin/python -m pytest \
  tests/test_workflows_ieee14_v2.py \
  tests_private/test_dynawo_node_breaker_france.py -q
```

`tests/test_workflows_ieee14_v2.py` covers the Eurostag-to-Dynawo workflow
without a plan JSON, a Dynawo JSON fault folder, the line-fault fallback,
multiple-jobs generation, line JSON parsing, and node/transformer case
generation. `tests_private/test_dynawo_node_breaker_france.py` parses the RTE
France IIDM fixture and verifies that node-breaker busbar sections are exposed
as EEAC buses.

Using `deeac_eurostag` with an explicit configuration object:

```python
from deeac.main import deeac_eurostag
from deeac.IO.arguments_parser import EurostagRunConfiguration

config = EurostagRunConfiguration(
    ech_file="/path/to/fech.ech",
    dta_file="/path/to/fdta.dta",
    lf_file="/path/to/fech.lf",
    execution_tree_file="/path/to/branch_1.json",
    execution_tree=None,
    seq_file=None,
    seq_file_folder="/path/to/case",
    seq_files=[
        "/path/to/case/B-C_fault.seq",
        "/path/to/case/A-B_fault.seq",
    ],
    island_threshold=0.0,
    cores=1,
    protection_delay=0.0,
    verbose=False,
    output_dir=None,
    json_path=None,
    rewrite=False,
    warn=False,
)

results = deeac_eurostag(config)
print(results.to_dict())
```

This is the recommended direct-Python form: give the common Eurostag files once
and provide the fault cases explicitly in `seq_files`. Use `seq_file` only for
the one-fault convenience case.

If you prefer, you can build `EurostagRunConfiguration` via `parse([...])` and pass it to `deeac_eurostag`.

Using `deeac_dynawo` with an explicit configuration object:

```python
from deeac.main import deeac_dynawo
from deeac.IO.arguments_parser import DynawoRunConfiguration

config = DynawoRunConfiguration(
    jobs_file="/path/to/network.jobs",
    iidm_file=None,
    dynawo_dyd_file=None,
    dynawo_par_file=None,
    dynawo_dyn_file=None,
    execution_tree_file="/path/to/branch_1.json",
    execution_tree=None,
    island_threshold=0.0,
    cores=1,
    protection_delay=0.0,
    verbose=False,
    output_dir=None,
    json_path=None,
    rewrite=False,
    warn=False,
)

results = deeac_dynawo(config)
print(results.to_dict())
```

This is the recommended Dynawo form: pass the case `.jobs` file and let the
parser resolve the IIDM and dynamic files. Manual mode is still available when
you need to provide `iidm_file`, `dynawo_dyd_file`, and `dynawo_par_file`
explicitly.

Both `deeac_eurostag` and `deeac_dynawo` delegate to `deeac_run(config)`, which
accepts either `EurostagRunConfiguration` or `DynawoRunConfiguration`.

For the explicit step-by-step flow, see `deeac/deeac_single_path.py` and
`trunk/quick_run_simple.py`.

## Graphical User Interface

The GUI allows you to run an Eurostag-based configuration or a Dynawo-based
configuration. The left side is used to load the case and choose the faults.
The right side is used to inspect the EEAC results and the structured logs.

The GUI mode can be run by executing the `main.py` file passing no arguments.

### Eurostag workflow

![deeac.png](docs/pics/deeac.png)

Use the Eurostag tab when you have one common Eurostag network and one or more
`.seq` files describing the disturbances to evaluate.

- `ECH file`
  Path to the Eurostag topology file. This defines the buses, branches,
  breakers, shunts, loads, and static generators of the network.
- `DTA file`
  Path to the Eurostag dynamic-data file. This gives the synchronous generator
  dynamic parameters needed by the EEAC computations.
- `LF file`
  Path to the Eurostag load-flow result file. This initializes the pre-fault
  operating point used as the starting state of the simulation.
- `Use Seq Folder`
  Enable this when the case contains many `.seq` files in one folder. This is
  the normal way to load a complete Eurostag case.
- `Seq file`
  Path to a single `.seq` file. Use this when you want to run only one fault.
- `Seq folder`
  Path to a folder containing many `.seq` files. Each `.seq` file becomes one
  fault entry in the fault list.
- `Execution plan`
  Path to the EEAC execution-plan JSON. This is the deterministic list of EEAC
  steps that will be run for every selected fault.
- `Output dir`
  Optional output directory. If it is filled, DEEAC writes per-fault output
  files there. If it is left empty, you can still inspect the results inside
  the GUI.
- `Island threshold (MW)`
  Threshold used to decide whether a post-fault island is large enough to keep
  during the network reduction steps.
- `Protection delay (ms)`
  Maximum allowed spread between the first and last protection-clearing action
  inside one `.seq` file. If the spread is larger than this value, the case is
  marked as degraded protection.
- `Cores`
  Number of worker processes used to run the selected faults in parallel.
- `Verbose`
  Enables detailed log messages in the `Logs` tab.
- `Warn on failure`
  Keeps a result with warnings when some candidate clusters fail. If disabled,
  those faults are more likely to be reported as full failures.

Typical Eurostag operator flow:

- Fill `ECH file`, `DTA file`, and `LF file`.
- Choose either one `Seq file` or a `Seq folder`.
- Fill `Execution plan`.
- Optionally fill `Output dir`.
- Click `Reload` to parse the network and populate the fault list.
- Select the faults you want to evaluate.
- Click `Run Simulation`.



### Dynawo workflow

The Dynawo workflow tab is the Dynawo equivalent of the Eurostag tab. It also
follows the same broad logic: load a configuration, parse it into a `Network`,
discover the available faults, and then run EEAC on the selected ones.


![deeac_dynawo.png](docs/pics/deeac_dynawo.png)

- `Use Dynawo .jobs file`
  Preferred mode. Use this for a normal Dynawo case. The `.jobs` file is the
  case entrypoint and points to the IIDM network, the DYD model file, the PAR
  parameter file, and the solver configuration.
- `Manual IIDM / DYD / PAR`
  Fallback mode. Use this only when you want to provide the main Dynawo files
  explicitly instead of relying on the `.jobs` file.
- `Dynawo .jobs file`
  Path to the `.jobs` case file. In preferred mode this is normally the only
  Dynawo input file you need to choose manually.
- `IIDM file`
  Manual-mode field. Path to the PowSybl IIDM network file.
- `DYD file`
  Manual-mode field. Path to the Dynawo dynamic-architecture file. DEEAC reads
  generator dynamic-model references and supported event models from this file.
- `PAR file`
  Manual-mode field. Path to the Dynawo parameter file that contains the
  numerical parameter values used by the DYD models.
- `Execution plan`
  Path to the EEAC execution-plan JSON, exactly as in the Eurostag workflow.
- `Output dir`
  Optional output directory for the generated per-fault files.
- `Island threshold (MW)`
  Threshold used to decide whether a post-fault island is large enough to keep.
- `Cores`
  Number of worker processes used to run the selected faults in parallel.
- `Verbose`
  Enables detailed log messages in the `Logs` tab.
- `Warn on failure`
  Keeps a result with warnings when some candidate clusters fail.

Typical Dynawo operator flow:

- Keep `Use Dynawo .jobs file` selected.
- Fill `Dynawo .jobs file`.
- Fill `Execution plan`.
- Optionally fill `Output dir`.
- Click `Reload` to parse the Dynawo case and populate the discovered fault list.
- Select the faults you want to evaluate.
- Click `Run Simulation`.

### Results tree

The `Results` tab shows one top-level row per executed fault. Expand a fault row
to inspect the individual result fields returned by the EEAC run.

- `Item`
  Name of the field.
- `Value`
  Value computed for that field.

The most important result fields are usually:

- `status`
  Overall EEAC outcome for the fault, for example stable, potentially stable,
  unstable, degraded protection, or computation failure.
- `CCT`
  Critical clearing time in seconds. This is usually the main quantity users
  compare between candidate faults.
- `critical_cluster`
  Generator cluster selected as critical for the final accepted result.
- `swing_state`
  OMIB swing direction used by the final accepted result.
- `node_id`
  Identifier of the last execution-plan node that produced the result.
- `warning`
  Non-fatal issues, such as failed candidate clusters when warning mode is
  enabled.
- `error_msg`
  Error description when the fault could not be evaluated normally.

The `Logs` tab contains the structured execution log grouped by fault. This is
the place to inspect when a result has warnings, when `CCT` is `None`, or when
you need to understand where the execution plan stopped.



## More docs

- [understanding_the_code.md](docs/understanding_the_code.md) explains the architecture and data flow.
- [paper.md](docs/paper.md) summarizes the EEAC paper used as the reference.
