"""End-to-end checks for the customer IEEE 14 examples."""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def test_customer_workflows(tmp_path: Path) -> None:
    """Evaluate both input formats and run generated cases when Dynawo is available.

    :param tmp_path: Isolated directory for example outputs.
    :return: None.
    """
    repository: Path = Path(__file__).resolve().parent.parent
    example: Path = repository / "examples" / "customer_workflows"
    jobs_file: Path = example / "dynawo_base" / "IEEE14.jobs"
    dynawo: Optional[str] = shutil.which("dynawo")
    if dynawo is not None:
        version: subprocess.CompletedProcess[str] = subprocess.run(
            [dynawo, "version"], capture_output=True, text=True, timeout=30, check=True,
        )
        if not version.stdout.strip().startswith("1.8."):
            dynawo = None
        else:
            pass
    else:
        pass
    for engine in ("eurostag", "dynawo"):
        results: Path = tmp_path / f"{engine}.json"
        cases: Path = tmp_path / engine
        command: list[str] = [sys.executable, "-m", "deeac.main", engine]
        if engine == "eurostag":
            command.extend(["-e", str(example / "eurostag" / "fech.ech"),
                            "-d", str(example / "eurostag" / "fdta.dta"),
                            "-l", str(example / "eurostag" / "fech.lf"),
                            "-f", str(example / "eurostag")])
        else:
            command.extend(["--fault-files", str(example / "faults")])
        command.extend(["--dynawo-jobs-file", str(jobs_file), "-t", str(example / "branch_1.json"),
                        "-c", "1", "-j", str(results), "--generation-dir", str(cases), "--no-line-fault"])
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            command, cwd=repository, capture_output=True, text=True, timeout=120,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        result_data: dict[str, object] = json.loads(results.read_text())
        assert set(result_data) == {"line1-2", "line1-5"}
        for fault_id in ("line1-2", "line1-5"):
            case_dir: Path = cases / fault_id
            assert (case_dir / "IEEE14.iidm").is_file()
            assert (case_dir / "IEEE14.jobs").is_file()
            assert (case_dir / f"fault_{fault_id}.par").is_file()
            assert not (case_dir / "outputs").exists()
            if dynawo is not None:
                simulation: subprocess.CompletedProcess[str] = subprocess.run(
                    [dynawo, "jobs", str(case_dir / "IEEE14.jobs")], capture_output=True, text=True, timeout=120,
                )
                assert simulation.returncode == 0, simulation.stderr
                timeline: str = (case_dir / "outputs" / "timeLine" / "timeline.log").read_text()
                assert "Fault (node) : begin" in timeline
                assert timeline.count("opening both sides") >= 2
            else:
                pass
