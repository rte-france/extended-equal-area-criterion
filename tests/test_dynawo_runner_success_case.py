"""End-to-end execution test for a known-good Dynawo input case."""

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import pytest

from deeac.DynawoPostProcess.runner import DynawoProcessResult, DynawoRunner


def test_dynawo_runner_executes_success_case(tmp_path: Path) -> None:
    """Exercise the runner with the repository's optional Dynawo 1.7 install.

    :param tmp_path: Temporary directory for the case and its outputs.
    :return: None.
    """
    install_dir: Path = Path(__file__).resolve().parent.parent / "Dynawo_Linux_v1.7.0" / "dynawo"
    if not install_dir.is_dir():
        pytest.skip("Dynawo 1.7 runner fixture installation not found")
    else:
        pass
    case_dir: Path = tmp_path / "case"
    shutil.copytree(Path(__file__).parent / "data" / "dynawo_success_case" / "inputs", case_dir,
                    ignore=shutil.ignore_patterns("outputs"))
    runner: DynawoRunner = DynawoRunner(dynawo_install_dir=str(install_dir))
    result: DynawoProcessResult = runner.run_jobs_file(str(case_dir / "IEEE14.jobs"), timeout_seconds=120.0)
    assert result.return_code == 0, result.stderr
    assert (case_dir / "outputs" / "logs" / "dynawo.log").is_file()
    assert (case_dir / "outputs" / "curves" / "curves.csv").is_file()


def test_dynawo_executes_success_case_and_stores_outputs(tmp_path: Path) -> None:
    """Run the fixture when the Dynawo launcher is available on PATH.

    :param tmp_path: Temporary directory for the case and its outputs.
    :return: None.
    """
    dynawo: Optional[str] = shutil.which("dynawo")
    if dynawo is None:
        pytest.skip("Dynawo launcher not found on PATH")
    else:
        pass

    inputs_dir: Path = Path(__file__).parent / "data" / "dynawo_success_case" / "inputs"
    case_dir: Path = tmp_path / "case"
    shutil.copytree(inputs_dir, case_dir, ignore=shutil.ignore_patterns("outputs"))

    version: subprocess.CompletedProcess[str] = subprocess.run(
        [dynawo, "version"], capture_output=True, text=True, timeout=30, check=True,
    )
    if version.stdout.strip().startswith("1.8."):
        # Dynawo 1.8 renamed indexed OmegaRef connections from the 1.7 fixture.
        dyd_file: Path = case_dir / "IEEE14.dyd"
        dyd_text: str = dyd_file.read_text(encoding="utf-8")
        dyd_text = re.sub(r'(var1="(?:omega_grp|omegaRef_grp|numcc_node|running_grp)_\d+)(")',
                          r'\1_\2', dyd_text)
        dyd_file.write_text(dyd_text, encoding="utf-8")
    else:
        pass

    result: subprocess.CompletedProcess[str] = subprocess.run(
        [dynawo, "jobs", str(case_dir / "IEEE14.jobs")], capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert (case_dir / "outputs" / "logs" / "dynawo.log").is_file()
    assert (case_dir / "outputs" / "curves" / "curves.csv").is_file()
