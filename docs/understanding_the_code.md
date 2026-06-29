This document explains the deeac codebase in simple, detailed terms and connects the implementation to the
Extended Equal Area Criterion (EEAC) paper:

Bahmanyar, A.; Ernst, D.; Vanaubel, Y.; Gemine, Q.; Pache, C.; Panciatici, P.
"Extended Equal Area Criterion Revisited: A Direct Method for Fast Transient Stability Analysis."
Energies 2021, 14, 7259. https://doi.org/10.3390/en14217259

The paper is summarized in `docs/paper.md` and the full PDF is in `docs/EEAC_paper.pdf`.

-------------------------------------------------------------------------------
High-level purpose
-------------------------------------------------------------------------------
This code implements the EEAC method for transient stability analysis of multi-machine power systems.
The core idea from the paper is:

1) A multi-machine system can be reduced to a One-Machine Infinite Bus (OMIB) equivalent by splitting
   generators into a critical cluster (CC) and a non-critical cluster (NC).
2) The Equal Area Criterion (EAC) is then applied to the OMIB to estimate the Critical Clearing Angle (CCA).
3) The Critical Clearing Time (CCT) is obtained from OMIB trajectory integration (Taylor series here).

The software uses Eurostag data files to build the power system, applies fault events, and runs the EEAC
pipeline for each fault.

-------------------------------------------------------------------------------
Code architecture and main modules
-------------------------------------------------------------------------------
The code is organized into three main layers:

1) Input parsing (IO)
   - `deeac/IO/eurostag/topology/topology_parser.py`
     Reads `.ech` and `.dta` and builds a `Network` (buses, branches, generators, loads).
   - `deeac/IO/eurostag/load_flow/load_flow_parser.py`
     Reads `.lf` and applies voltages, powers, taps, and admittances directly to the `Network`.
   - `deeac/IO/eurostag/events/event_parser.py`
     Reads `.seq` fault files and produces event objects.
   - `deeac/IO/iidm/iidm_parser.py`
     Reads IIDM (PowSybl) networks into a `Network` object.
   - `deeac/IO/dynawo/dynawo_parser.py`
     Parses Dynawo `.dyd`/`.par` files to augment IIDM generators with inertia and reactance.
   - `deeac/IO/dynawo/dynawo_event_parser.py`
     Parses Dynawo `.dyn` event files for Dynawo-based runs. The class exists in the
     execution path, but its parsing logic is still a stub and raises `NotImplementedError`.
   - `deeac/IO/event_loader.py`
     Splits parsed events into failure and mitigation lists.
   - `deeac/IO/arguments_parser.py`
     Parses CLI and global JSON configuration into a `EurostagRunConfiguration` or `DynawoRunConfiguration`.
   - `deeac/IO/plan_loader.py`
     Reads the execution plan JSON (now a linear list of nodes, not a tree).
   - `deeac/IO/plan_models.py`
     Defines the execution plan node models.
   - `deeac/IO/inputs.py`
     Defines `EEACInputs`, the input bundle passed to the EEAC pipeline.

2) Core model (Models)
   - `deeac/Models/network.py`
     Pure data model for the grid (buses, branches, generators, loads).
     The network is treated as read-only after parsing; no caches are stored inside it.
   - `deeac/Models/network.py` also contains:
     - `SimplifiedNetwork` and `NetworkStateView`: reduced, analysis-ready views.
     - `NetworkComputed`: explicit cache object for computed state (simplified networks,
       reduced admittances, generator voltage matrix).
   - `deeac/Models/*` provide bus/line/transformer/generator models.

3) EEAC pipeline (Simulations)
   - `deeac/Simulations/eeac.py`
     Orchestrates the identifier -> evaluator -> selector steps.
   - `deeac/Simulations/identifiers/critical_clusters_identifier.py`
     Builds the identifier (currently DFT-based).
   - `deeac/Simulations/identifiers/during_fault_trajectory_identifier.py`
     Uses Taylor series rotor-angle prediction to rank critical generators.
   - `deeac/Simulations/OMIB/omib.py`, `deeac/Simulations/OMIB/zoomib.py`
     Build OMIB and compute electrical power curves and OMIB properties.
   - `deeac/Simulations/eac.py`
     Applies Equal Area Criterion to determine CCA and maximum angle.
   - `deeac/Simulations/RotorAngleTrajectoryCalculator/omib_series.py`
     Computes CCT from CCA using Taylor series integration.

Entry points:
   - `deeac/deeac_all_paths.py`: shared Eurostag/Dynawo execution flow.
     `deeac_run` contains the common pipeline, while `deeac_eurostag` and
     `deeac_dynawo` are thin wrappers for the two configuration types.
   - `deeac/deeac_single_path.py`: explicit step-by-step execution flow.

-------------------------------------------------------------------------------
How data flows (end-to-end)
-------------------------------------------------------------------------------
1) Parse configuration
   - CLI args or global JSON are parsed into a `EurostagRunConfiguration` or `DynawoRunConfiguration`.

2) Build the network
   - Topology parser reads `.ech` and `.dta` into a `Network`.
   - Load-flow parser reads `.lf` and applies voltages, taps, and powers.

3) Build the pre-fault simplified network
   - A `NetworkComputed` instance is created by the caller.
   - `Network.initialize_simplified_network(computed)` builds the PRE_FAULT state.
   - Simplification (from the paper's OMIB setup assumptions) includes:
     - Merging buses connected by closed breakers.
     - Removing opened branches or disconnected components.
     - Creating fictive internal-voltage buses for generators (classic transient model).

4) For each fault or event file
   a) Parse events
      - `EventLoader` uses `EurostagEventParser` for Eurostag `.seq` inputs or
        `DynawoEventParser` for Dynawo `.dyn` inputs.
   b) Apply events and build states
      - `apply_events_to_network(network, computed, failure_events, mitigation_events)`
        computes DURING_FAULT and POST_FAULT simplified networks.
   c) Build generator snapshot
      - `GeneratorSnapshot` captures arrays of generator data for fast numeric operations.
   d) Run the EEAC plan
      - Identifier: pick candidate critical clusters (DFT-based).
      - Evaluator: build OMIB, apply EAC, compute CCA/CCT.
      - Selector: choose the most critical candidate (min CCT).
   e) Return `EEACResult` and aggregate into `EEACResults`.

5) Output
   - Results can be returned to the caller and/or written to JSON.
   - Each fault has a result with `status`, `CCT`, `critical_cluster`, `swing_state`, etc.

-------------------------------------------------------------------------------
How the paper maps to code
-------------------------------------------------------------------------------
Key paper sections and their matching code:

- Paper Section 2 (OMIB concept and EAC)
  - `deeac/Simulations/OMIB/omib.py` and `deeac/Simulations/OMIB/zoomib.py`
  - `deeac/Simulations/eac.py`

- Paper Section 3 (critical machines identification and clustering)
  - `deeac/Simulations/identifiers/during_fault_trajectory_identifier.py`
  - `deeac/Simulations/identifiers/critical_clusters_identifier.py`

- Paper Section 4 (Taylor series and CCT)
  - `deeac/Simulations/RotorAngleTrajectoryCalculator/omib_series.py`

- Paper Section 5 (full EEAC scheme)
  - `deeac/Simulations/eeac.py` orchestrates the linear execution plan.

-------------------------------------------------------------------------------
Inputs
-------------------------------------------------------------------------------
Required files:
  - `.ech` : static network topology (buses, lines, transformers, breakers, loads).
  - `.dta` : dynamic generator data (reactances, inertia constants).
  - `.lf`  : load-flow results (voltages, tap positions, powers).
  - `.seq` : fault events (short circuits, breaker operations) for Eurostag runs.
  - `.iidm` + `.dyd` + `.par` + `.dyn` for IIDM + Dynawo runs.

Configuration:
  - Execution plan JSON (linear list of nodes; the tree logic is removed).
  - Global JSON configuration (`-g`) that includes all paths and flags.

Key CLI arguments (see `deeac/deeac_all_paths.py`):
  - `-e`, `-d`, `-l`: ech/dta/lf file paths
  - `-s` or `-f`: single or multiple seq files
  - `-t`: execution plan
  - `-o` / `-j`: output directory / output JSON
  - `-i`, `-p`: islanding threshold, protection delay
  - `-v`, `-w`: verbose logging, warn flag
  - `--iidm-file`, `--dynawo-dyd-file`, `--dynawo-par-file`, `--dynawo-dyn-file`: Dynawo/IIDM inputs

-------------------------------------------------------------------------------
Outputs
-------------------------------------------------------------------------------
Main output object: `EEACResults`
  - A collection of `EEACResult` entries, one per fault.
  - Fields (if applicable):
    - `status`: stability outcome (POTENTIALLY STABLE, ALWAYS STABLE, Error, etc.)
    - `CCT`: critical clearing time (seconds)
    - `critical_cluster`: comma-separated generator names
    - `swing_state`: FORWARD or BACKWARD
    - `warning` / `error_msg` when needed

Optional JSON output:
  - When `-o` or `-j` is used, results are written as JSON.

-------------------------------------------------------------------------------
Key internal data structures (simple overview)
-------------------------------------------------------------------------------
Network (read-only):
  - Buses, branches, generators, loads, capacitor banks, breakers.
  - No hidden caches. All computed state lives in `NetworkComputed`.

NetworkComputed (explicit cache):
  - Simplified networks for PRE/DURING/POST fault.
  - Reduced admittance arrays per state.
  - Generator index map and voltage product matrix.

SimplifiedNetwork:
  - Reduced graph used for computations.
  - Provides reduced admittance matrices (dense and sparse).

GeneratorSnapshot:
  - Arrays of rotor angles, voltages, powers, inertia coefficients.
  - Used for vectorized math in identifiers and OMIB calculations.

-------------------------------------------------------------------------------
Where performance comes from
-------------------------------------------------------------------------------
The current implementation focuses on fast, deterministic computation:
  - Generator snapshots are numpy arrays, not per-object loops.
  - Reduced admittance matrices can be dense or sparse.
  - OMIB inner loop is vectorized.
  - Cached matrices live in `NetworkComputed` and are passed explicitly.

-------------------------------------------------------------------------------
Debug/visualization helpers
-------------------------------------------------------------------------------
`deeac/Models/network.py` contains plotting helpers that require:
  - `Network`
  - `NetworkComputed`
  - Explicit `failure_events` (no event state inside the network).

-------------------------------------------------------------------------------
Summary
-------------------------------------------------------------------------------
This codebase implements the EEAC method as described in the paper by:
  - Parsing Eurostag data into a clean, read-only `Network`.
  - Building simplified network states for PRE/DURING/POST fault.
  - Identifying critical generator clusters.
  - Building an OMIB equivalent and applying EAC to compute CCA/CCT.
  - Selecting the most critical candidate and returning structured results.

The `NetworkComputed` cache makes the pipeline explicit, testable, and fast while
keeping the core `Network` model immutable after parsing.
