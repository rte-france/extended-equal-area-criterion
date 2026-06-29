"""
End-to-end execution test for a known-good Dynawo input case.
"""

import os
import shutil

import pytest

from deeac.DynawoPostProcess.runner import DynawoRunner


def get_repo_root_dir() -> str:
    """
    Return repository root directory.

    :return: Repository root directory.
    """
    tests_dir: str = os.path.dirname(__file__)
    repo_root_dir: str = os.path.abspath(os.path.join(tests_dir, ".."))
    return repo_root_dir


def get_dynawo_install_dir() -> str:
    """
    Return local vanilla Dynawo install directory.

    :return: Dynawo install directory.
    """
    repo_root_dir: str = get_repo_root_dir()
    install_dir: str = os.path.join(repo_root_dir, "Dynawo_Linux_v1.7.0", "dynawo")
    return install_dir


def get_success_case_inputs_dir() -> str:
    """
    Return copied known-good Dynawo case fixture directory.

    :return: Fixture input directory.
    """
    tests_dir: str = os.path.dirname(__file__)
    inputs_dir: str = os.path.join(tests_dir, "data", "dynawo_success_case", "inputs")
    return inputs_dir


def test_dynawo_runner_executes_success_case_and_stores_outputs() -> None:
    """
    Execute a known-good Dynawo case and verify generated output artifacts.

    :return: Return value.
    """
    install_dir: str = get_dynawo_install_dir()
    if os.path.isdir(install_dir):
        pass
    else:
        pytest.skip(f"Dynawo install directory not found: {install_dir}")

    inputs_dir: str = get_success_case_inputs_dir()
    jobs_path: str = os.path.join(inputs_dir, "IEEE14.jobs")

    # The fixture stores outputs alongside jobs; remove previous run outputs for deterministic checks.
    outputs_dir: str = os.path.join(inputs_dir, "outputs")
    if os.path.isdir(outputs_dir):
        shutil.rmtree(outputs_dir)
    else:
        pass

    runner = DynawoRunner(
        dynawo_binary_path=None,
        dynawo_install_dir=install_dir,
        dynawo_binary_options=None,
    )
    result = runner.run_jobs_file(jobs_file=jobs_path, timeout_seconds=120.0)

    assert result.return_code == 0, result.stderr
    assert os.path.isdir(outputs_dir)
    assert os.path.isfile(os.path.join(outputs_dir, "logs", "dynawo.log"))
    assert os.path.isfile(os.path.join(outputs_dir, "curves", "curves.csv"))
