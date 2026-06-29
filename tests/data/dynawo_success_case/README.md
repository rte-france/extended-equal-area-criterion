# Dynawo Success Case Fixture

This fixture is copied from the vanilla Dynawo 1.7.0 example:

- source: `Dynawo_Linux_v1.7.0/dynawo/examples/DynaSwing/IEEE14/IEEE14_Fault`
- copied inputs: `IEEE14.jobs`, `IEEE14.dyd`, `IEEE14.par`, `IEEE14.iidm`, `IEEE14.crv`

The end-to-end pytest `tests/test_dynawo_runner_success_case.py` executes this case
using the local `DynawoRunner` and stores outputs under:

- `tests/data/dynawo_success_case/inputs/outputs`
