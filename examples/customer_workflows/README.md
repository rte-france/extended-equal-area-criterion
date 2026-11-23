# IEEE 14: EEAC and Dynawo examples

These examples evaluate two independent line faults on the IEEE 14 network.
For the customer workflow, use [MANUAL_DYNAWO.md](MANUAL_DYNAWO.md) to run
EEAC and collect the prepared cases for manual Dynawo simulation. The optional
integrated examples below also launch Dynawo. The supplied base case contains
no fault; it is copied before scenarios are added.

The examples use Dynawo **1.8** and its `NodeFault` model. Each line is split
at the fault location because this Dynawo installation does not provide the
`LineFault` model. The examples use the same network and fault positions for
the Eurostag and Dynawo inputs.

## Before starting

Install DEEAC from the repository and make sure Dynawo 1.8 is installed. Run
the commands below from the repository root. Replace `/path/to/dynawo` with the
installation directory containing `bin`, `lib`, `share` and `ddb`.

```sh
python -m pip install -e .
```

The output paths below must not already contain generated cases. To repeat an
example, choose a new results file and generation directory.

## 1. Eurostag input → EEAC → Dynawo

DEEAC reads the `.ech`, `.dta`, and `.lf` network files and both `.seq` files.
It maps the selected line faults to the supplied Dynawo base case, then runs
each generated simulation.

```sh
deeac eurostag \
  -e examples/customer_workflows/eurostag/fech.ech \
  -d examples/customer_workflows/eurostag/fdta.dta \
  -l examples/customer_workflows/eurostag/fech.lf \
  -f examples/customer_workflows/eurostag \
  -t examples/customer_workflows/branch_1.json -c 1 \
  -j /tmp/eeac-eurostag-results.json \
  --dynawo-jobs-file examples/customer_workflows/dynawo_base/IEEE14.jobs \
  --generation-dir /tmp/eeac-eurostag-cases \
  --no-line-fault --dynawo-install-dir /path/to/dynawo
```

## 2. Dynawo input → EEAC → Dynawo

DEEAC reads the fault-free Dynawo case and the two external JSON fault files.
It then prepares and runs a separate Dynawo case for each fault.

```sh
deeac dynawo \
  --dynawo-jobs-file examples/customer_workflows/dynawo_base/IEEE14.jobs \
  --fault-files examples/customer_workflows/faults \
  -t examples/customer_workflows/branch_1.json -c 1 \
  -j /tmp/eeac-dynawo-results.json \
  --generation-dir /tmp/eeac-dynawo-cases \
  --no-line-fault --dynawo-install-dir /path/to/dynawo
```

To prepare only one case, add `--selected-fault line1-2`. Without that option,
all faults are prepared. To prepare cases without running Dynawo, omit
`--dynawo-install-dir`.

## What to show

Open the results JSON to see the EEAC result and critical clearing time (`CCT`,
in seconds) for each fault. The example was checked locally with these results:

| Fault | Eurostag input CCT | Dynawo input CCT |
| --- | ---: | ---: |
| Line 1–2 | 0.479430 s | 0.479446 s |
| Line 1–5 | 0.500259 s | 0.500260 s |

The small differences reflect the two input representations. These are EEAC
estimates; a successful Dynawo run at the specified 0.1 s clearing time does
not independently establish the CCT.

For each generated case, inspect:

- `outputs/curves/curves.csv` for bus voltages and generator responses.
- `outputs/timeLine/timeline.log` for the fault and line disconnections.
- `outputs/logs/dynawo.log` for the simulation log.

For example, in the Dynawo-input run, these are under
`/tmp/eeac-dynawo-cases/line1-2/`. The fault starts at 10.0 s and clears at
10.1 s; the timeline shows both split line segments opening at clearance.

The Dynawo input files are adapted from the Dynawo 1.7 IEEE 14 fault fixture in
`tests/data/dynawo_success_case`: the existing fault was removed, OmegaRef and
curve names were updated for Dynawo 1.8, and timeline output was enabled. The
Eurostag inputs and EEAC plan are copies of the repository's IEEE 14 fixtures.
