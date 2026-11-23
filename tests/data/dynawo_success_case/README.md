# Dynawo Success Case Fixture

This fixture is copied from the vanilla Dynawo 1.7.0 example:

- source: `Dynawo_Linux_v1.7.0/dynawo/examples/DynaSwing/IEEE14/IEEE14_Fault`
- copied inputs: `IEEE14.jobs`, `IEEE14.dyd`, `IEEE14.par`, `IEEE14.iidm`, `IEEE14.crv`

The end-to-end pytest `tests/test_dynawo_runner_success_case.py` looks for the
`dynawo` launcher on PATH and skips when it is unavailable. It runs a temporary
copy of the case and adjusts the OmegaRef connections for Dynawo 1.8.
