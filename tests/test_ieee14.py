"""
Integration tests for the IEEE14 sample data.
"""

import os
import shutil
from pathlib import Path

import numpy as np

from deeac.main import DynawoRunConfiguration, EurostagRunConfiguration, deeac_dynawo, deeac_eurostag

TESTS_DIR: str = os.path.dirname(__file__)
IEEE14_DIR: str = os.path.join(TESTS_DIR, "data", "IEEE14")
EUROSTAG_DIR: str = os.path.join(IEEE14_DIR, "Eurostag")
DYNAWO_DIR: str = os.path.join(IEEE14_DIR, "Dynawo")
PLAN_PATH: str = os.path.join(IEEE14_DIR, "branch_1.json")


def copy_ieee14_format_dir(source_dir: str, tmp_path: Path, folder_name: str) -> str:
    """
    Copy one IEEE14 input-format directory into pytest's temporary workspace.

    The issue #37 regressions need to mutate generator source metadata. Copying the
    case first keeps the shared IEEE14 fixtures stable for all other tests and lets
    the full DEEAC path read normal files from disk.

    :param source_dir: Original IEEE14 format directory.
    :param tmp_path: Pytest temporary directory.
    :param folder_name: Name of the copied case folder.
    :return: Copied case directory.
    """
    copied_dir: Path = tmp_path / folder_name

    # The sample directories are tiny, so copying the whole format folder is the
    # simplest future-proof way to keep relative references in jobs files intact.
    shutil.copytree(src=source_dir, dst=copied_dir)

    return str(copied_dir)


def replace_file_text(file_path: str, old_text: str, new_text: str, replacement_count: int) -> None:
    """
    Replace a bounded amount of text in a fixture copy.

    The source fields are part of fixed external formats. The tests only need to
    emulate a user changing generator technologies, so this helper keeps the edit
    explicit and avoids creating permanent near-duplicate fixture files.

    :param file_path: File to mutate.
    :param old_text: Text expected in the copied fixture.
    :param new_text: Replacement text.
    :param replacement_count: Number of replacements to perform.
    :return: Return value.
    """
    # Read and write through normal text files because both IIDM and ECH samples
    # are small input fixtures and this preserves the rest of the case verbatim.
    with open(file_path, "r", encoding="utf-8") as input_file:
        contents: str = input_file.read()

    updated_contents: str = contents.replace(old_text, new_text, replacement_count)

    with open(file_path, "w", encoding="utf-8") as output_file:
        output_file.write(updated_contents)


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


def test_ieee_14_eurostag_runs_with_one_nuclear_generator(tmp_path: Path) -> None:
    """
    Run Eurostag DEEAC when the RTE nuclear-only pass has fewer than two machines.

    Issue #37 reported that DEEAC failed when fewer than two generators had a
    Nuclear source. The RTE customization still runs the normal NO_HYDRO pass,
    but the Nuclear-only pass cannot form a meaningful split with only one
    Nuclear machine. This test changes two of the three Nuclear units to Coal in
    a temporary ECH copy and confirms the full Eurostag execution still returns a
    result.

    :param tmp_path: Pytest temporary directory.
    :return: Return value.
    """
    case_dir: str = copy_ieee14_format_dir(
        source_dir=EUROSTAG_DIR,
        tmp_path=tmp_path,
        folder_name="Eurostag_one_nuclear",
    )
    replace_file_text(
        file_path=os.path.join(case_dir, "fech.ech"),
        old_text="Nucleair",
        new_text="Charbon ",
        replacement_count=2,
    )

    config = EurostagRunConfiguration(
        ech_file=os.path.join(case_dir, "fech.ech"),
        dta_file=os.path.join(case_dir, "fdta.dta"),
        lf_file=os.path.join(case_dir, "fech.lf"),
        execution_tree_file=PLAN_PATH,
        execution_tree=None,
        seq_file=None,
        seq_file_folder=case_dir,
        seq_files=[
            os.path.join(case_dir, "line1-5.seq"),
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
    res = results.get("line1-5")

    assert res is not None
    assert res.critical_cluster != ""


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


def test_ieee_14_dynawo_runs_with_one_nuclear_generator(tmp_path: Path) -> None:
    """
    Run Dynawo DEEAC when the RTE nuclear-only pass has fewer than two machines.

    This mirrors the Eurostag regression with the IIDM source metadata used by
    the Dynawo parser. Two Nuclear IIDM generators are changed to Solar in a
    temporary case copy, leaving exactly one Nuclear generator for the RTE
    customization to see.

    :param tmp_path: Pytest temporary directory.
    :return: Return value.
    """
    case_dir: str = copy_ieee14_format_dir(
        source_dir=DYNAWO_DIR,
        tmp_path=tmp_path,
        folder_name="Dynawo_one_nuclear",
    )
    replace_file_text(
        file_path=os.path.join(case_dir, "IEEE14.iidm"),
        old_text='energySource="NUCLEAR"',
        new_text='energySource="SOLAR"',
        replacement_count=2,
    )

    config = DynawoRunConfiguration(
        jobs_file=os.path.join(case_dir, "IEEE14.jobs"),
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
    res = results.get("line1_5")

    assert res is not None
    assert res.critical_cluster != ""
