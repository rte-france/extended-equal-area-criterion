"""
Integration tests for the IEEE14 sample data.
"""

import os
import numpy as np

from deeac.main import DynawoRunConfiguration, EurostagRunConfiguration, deeac_dynawo, deeac_eurostag

TESTS_DIR: str = os.path.dirname(__file__)
IEEE14_DIR: str = os.path.join(TESTS_DIR, "data", "IEEE14")
EUROSTAG_DIR: str = os.path.join(IEEE14_DIR, "Eurostag")
DYNAWO_DIR: str = os.path.join(IEEE14_DIR, "Dynawo")
PLAN_PATH: str = os.path.join(IEEE14_DIR, "branch_1.json")


def test_ieee_14_eurostag() -> None:
    """
    Run the IEEE14 Eurostag sample with the files shipped in ``tests/data``.
    """
    config = EurostagRunConfiguration(
        ech_file=os.path.join(EUROSTAG_DIR, "fech.ech"),
        dta_file=os.path.join(EUROSTAG_DIR, "fdta.dta"),
        lf_file=os.path.join(EUROSTAG_DIR, "fech.lf"),
        execution_tree_file=PLAN_PATH,
        execution_tree=None,
        seq_file=None,
        seq_file_folder=EUROSTAG_DIR,
        seq_files=[
            os.path.join(EUROSTAG_DIR, "line1-5.seq"),
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

    results = deeac_eurostag(config)

    assert results is not None
    res = results.get("line1-5")

    assert np.isclose(res.cct, 0.5002585629065066)
    assert res.critical_cluster == 'GEN    1'


def test_ieee_14_dynawo() -> None:
    """
    Run the IEEE14 Dynawo sample from its explicit configuration object.
    """
    config = DynawoRunConfiguration(
        jobs_file=os.path.join(DYNAWO_DIR, "IEEE14.jobs"),
        iidm_file=None,
        dynawo_dyd_file=None,
        dynawo_par_file=None,
        dynawo_dyn_file=None,
        execution_tree_file=PLAN_PATH,
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

    results = deeac_dynawo(config)

    assert results is not None
    res = results.get("line1_5")
    assert np.isclose(res.cct, 0.5002585629065066)
    assert res.critical_cluster == 'GEN    1'
