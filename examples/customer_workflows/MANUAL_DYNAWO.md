# Prepare Dynawo cases for manual simulation

These examples run EEAC and prepare the Dynawo input files for two IEEE 14
line faults. Each fault gets its own complete case folder. You can collect those
folders and run them with Dynawo whenever and wherever you choose.

**Dynawo is not launched by these commands and does not need to be installed
on the machine running EEAC.** The supplied base files are configured for
Dynawo 1.8. The Python dependencies needed to read Dynawo network data,
including PyPowSyBl, are still required by DEEAC.

Run these commands from the repository root, after installing DEEAC:

```sh
python -m pip install -e .
```

The output directories below must not contain previously generated cases. To
run an example again, choose a new results file and output directory.

## Eurostag inputs

DEEAC reads the Eurostag network and the two sequence files, evaluates the
faults, and prepares a Dynawo case for each one:

```sh
deeac eurostag \
  -e examples/customer_workflows/eurostag/fech.ech \
  -d examples/customer_workflows/eurostag/fdta.dta \
  -l examples/customer_workflows/eurostag/fech.lf \
  -f examples/customer_workflows/eurostag \
  -t examples/customer_workflows/branch_1.json -c 1 \
  -j /tmp/eeac-manual-eurostag-results.json \
  --dynawo-jobs-file examples/customer_workflows/dynawo_base/IEEE14.jobs \
  --generation-dir /tmp/eeac-manual-eurostag-cases \
  --no-line-fault
```

## Dynawo inputs

DEEAC reads the fault-free Dynawo network and two external JSON fault files,
evaluates them, and prepares a Dynawo case for each one:

```sh
deeac dynawo \
  --dynawo-jobs-file examples/customer_workflows/dynawo_base/IEEE14.jobs \
  --fault-files examples/customer_workflows/faults \
  -t examples/customer_workflows/branch_1.json -c 1 \
  -j /tmp/eeac-manual-dynawo-results.json \
  --generation-dir /tmp/eeac-manual-dynawo-cases \
  --no-line-fault
```

To prepare just one fault in either command, add `--selected-fault line1-2`.
The EEAC results file still contains the results of the evaluated faults.

## Files to collect

Each output directory contains `line1-2/` and `line1-5/`. Collect the entire
folder for each simulation; it contains `IEEE14.jobs`, the copied IIDM network,
DYD, PAR and curve files, plus the generated fault parameter file. File paths
in the jobs and model files are relative to the case folder.

No simulation `outputs/` folder is created during preparation. After copying a
case to a machine with Dynawo 1.8 installed, for example, run:

```sh
dynawo jobs /path/to/line1-2/IEEE14.jobs
```

The example uses a split line and a `NodeFault` (`--no-line-fault`). Its fault
starts at 10.0 s and clears at 10.1 s. See [README.md](README.md) for the
optional integrated runs, expected EEAC results and simulation outputs.
