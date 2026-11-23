"""Workflow examples using the IEEE14_v2 sample inputs.

The IEEE14_v2 directory intentionally has no EEAC execution-plan JSON. These
examples rely on the workflow's built-in in-memory plan instead.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict
from xml.etree import ElementTree as ET

import pytest

from deeac.IO.arguments_parser import EurostagRunConfiguration
from deeac.IO.plan_models import ExecutionPlan
from deeac.workflows import (
    default_execution_plan,
    derive_default_disconnections,
    parse_dynawo_fault_json,
    prepare_dynawo_line_fault_cases,
    resolve_fault_files,
    run_eurostag_to_dynawo_workflow,
)


TESTS_DIR: Path = Path(__file__).resolve().parent
IEEE14_V2_DIR: Path = TESTS_DIR / "data" / "IEEE14_v2"
EUROSTAG_DIR: Path = IEEE14_V2_DIR / "Eurostag"
DYNAWO_DIR: Path = IEEE14_V2_DIR / "Dynawo"


def make_line_fault(fault_id: str, buses: tuple[str, str], line_suffix: str) -> Dict[str, object]:
    """Build a fault JSON matching one IEEE14_v2 line-fault fixture.

    :param fault_id: Fault ID matching a Eurostag sequence file stem.
    :param buses: DEEAC bus names and corresponding Dynawo terminal names.
    :param line_suffix: Numeric line suffix used by the IEEE14_v2 IIDM IDs.
    :return: JSON-compatible fault description.
    """
    first_bus: str = buses[0]
    second_bus: str = buses[1]
    return {
        "fault_id": fault_id,
        "fault_type": "line",
        "target": {
            "first_bus": first_bus,
            "second_bus": second_bus,
            "parallel_id": "1",
            "static_id": f"_BUS____{line_suffix[0]}-BUS____{line_suffix[-1]}-1_AC",
            "terminal_1": f"_BUS____{line_suffix[0]}_TN",
            "terminal_2": f"_BUS____{line_suffix[-1]}_TN",
        },
        "impedance": {"r": 0.0, "x": 0.0},
        "start_time": 10.0,
        "end_time": 10.1,
        "distance": 0.01,
        "disconnections": [
            {
                "first_bus": first_bus,
                "second_bus": second_bus,
                "parallel_id": "1",
                "time": 10.1,
            }
        ],
    }


def test_dynawo_cli_runs_external_fault(tmp_path: Path) -> None:
    """Run the Dynawo CLI with an external fault and save its result.

    :param tmp_path: Temporary directory provided by pytest.
    :return: Return value.
    """
    pytest.importorskip("pypowsybl")
    fault_file: Path = tmp_path / "fault.json"
    fault_file.write_text(json.dumps(make_line_fault("line1-2", ("BUS    1", "BUS    2"), "1-2")))
    result_file: Path = tmp_path / "results" / "critical_cluster_results.json"
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        [sys.executable, "-c", "from deeac.main import run; run()", "dynawo",
         "--dynawo-jobs-file", str(DYNAWO_DIR / "IEEE14_JOBS.xml"), "--fault-files", str(fault_file),
         "--generation-dir", str(tmp_path / "generated"), "--no-line-fault", "--selected-fault", "line1-2",
         "-t", str(TESTS_DIR / "data" / "IEEE14" / "branch_1.json"), "-c", "1", "-o", str(result_file.parent)],
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "line1-2" in json.loads(result_file.read_text())
    assert (tmp_path / "generated" / "line1-2" / "IEEE14_IIDM.xml").is_file()


def test_eurostag_cli_generates_dynawo_case(tmp_path: Path) -> None:
    """Run Eurostag EEAC and generate one selected Dynawo case from the CLI.

    :param tmp_path: Temporary directory provided by pytest.
    :return: None.
    """
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        [sys.executable, "-c", "from deeac.main import run; run()", "eurostag",
         "-e", str(EUROSTAG_DIR / "fech.ech"), "-d", str(EUROSTAG_DIR / "fdta.dta"),
         "-l", str(EUROSTAG_DIR / "fech.lf"), "-f", str(EUROSTAG_DIR),
         "-t", str(TESTS_DIR / "data" / "IEEE14" / "branch_1.json"), "-c", "1",
         "--dynawo-jobs-file", str(DYNAWO_DIR / "IEEE14_JOBS.xml"),
         "--generation-dir", str(tmp_path / "generated"), "--selected-fault", "line1-2", "--no-line-fault"],
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert (tmp_path / "generated" / "line1-2" / "IEEE14_IIDM.xml").is_file()
    assert not (tmp_path / "generated" / "line1-5").exists()


def test_dynawo_cli_generates_selected_multiple_job(tmp_path: Path) -> None:
    """Validate selected fault IDs against batch scenario IDs.

    :param tmp_path: Temporary directory provided by pytest.
    :return: None.
    """
    pytest.importorskip("pypowsybl")
    fault_file: Path = tmp_path / "fault.json"
    fault_file.write_text(json.dumps(make_line_fault("line1-2", ("BUS    1", "BUS    2"), "1-2")))
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        [sys.executable, "-c", "from deeac.main import run; run()", "dynawo",
         "--dynawo-jobs-file", str(DYNAWO_DIR / "IEEE14_JOBS.xml"), "--fault-files", str(fault_file),
         "--generation-dir", str(tmp_path / "generated"), "--multiple-jobs", "--selected-fault", "line1-2",
         "-t", str(TESTS_DIR / "data" / "IEEE14" / "branch_1.json"), "-c", "1"],
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert (tmp_path / "generated" / "multiple" / "IEEE14_JOBS.multiple").is_file()


def test_ieee14_v2_eurostag_to_dynawo_uses_default_plan_without_plan_json(tmp_path: Path) -> None:
    """Run both Eurostag sequence files and prepare Dynawo cases without a plan JSON.

    :param tmp_path: Temporary directory provided by pytest.
    :return: Return value.
    """
    config: EurostagRunConfiguration = EurostagRunConfiguration(
        ech_file=str(EUROSTAG_DIR / "fech.ech"),
        dta_file=str(EUROSTAG_DIR / "fdta.dta"),
        lf_file=str(EUROSTAG_DIR / "fech.lf"),
        execution_tree_file=None,
        execution_tree=None,
        seq_file=None,
        seq_file_folder=str(EUROSTAG_DIR),
        seq_files=[str(EUROSTAG_DIR / "line1-2.seq"), str(EUROSTAG_DIR / "line1-5.seq")],
        island_threshold=0.0,
        cores=1,
        protection_delay=0.0,
        output_dir=None,
        json_path=None,
        rewrite=True,
        warn=True,
    )

    results, generated_folders = run_eurostag_to_dynawo_workflow(
        config=config,
        dynawo_jobs_file=str(DYNAWO_DIR / "IEEE14_JOBS.xml"),
        generation_dir=str(tmp_path / "dynawo_cases"),
    )

    assert isinstance(config.execution_tree, ExecutionPlan)
    assert config.execution_tree_file is None
    assert not (IEEE14_V2_DIR / "branch_1.json").exists()
    assert results.get("line1-2") is not None
    assert results.get("line1-5") is not None
    assert len(generated_folders) == 2


def test_ieee14_v2_dynawo_fault_folder_generates_one_case_per_fault(tmp_path: Path) -> None:
    """Create two separate Dynawo cases from generated JSON fault descriptions.

    The fixture has XML event examples but no fault JSON files. The test writes
    the proposed JSON inputs into pytest's temporary directory and leaves the
    checked-in IEEE14_v2 data untouched.

    :param tmp_path: Temporary directory provided by pytest.
    :return: Return value.
    """
    fault_dir: Path = tmp_path / "faults"
    fault_dir.mkdir()
    line_1_2: Dict[str, object] = make_line_fault("line1-2", ("BUS    1", "BUS    2"), "1-2")
    line_1_5: Dict[str, object] = make_line_fault("line1-5", ("BUS    1", "BUS    5"), "1-5")
    (fault_dir / "line1-2.json").write_text(json.dumps(line_1_2), encoding="utf-8")
    (fault_dir / "line1-5.json").write_text(json.dumps(line_1_5), encoding="utf-8")

    fault_paths: list[str] = resolve_fault_files(str(fault_dir))
    generated_folders: list[str] = prepare_dynawo_line_fault_cases(
        jobs_file=str(DYNAWO_DIR / "IEEE14_JOBS.xml"),
        fault_files=str(fault_dir),
        output_dir=str(tmp_path / "generated"),
    )

    assert len(generated_folders) == 2
    for fault_id in ("line1-2", "line1-5"):
        case_dir: Path = tmp_path / "generated" / fault_id
        jobs_file: Path = case_dir / "IEEE14_JOBS.xml"
        dyd_file: Path = case_dir / "IEEE14_DYD.xml"
        par_file: Path = case_dir / f"fault_{fault_id}.par"
        iidm_file: Path = case_dir / "IEEE14_IIDM.xml"
        assert jobs_file.is_file()
        assert dyd_file.is_file()
        assert par_file.is_file()
        assert iidm_file.is_file()
        generated_models: list[ET.Element] = list(ET.parse(dyd_file).getroot())
        assert any(model.get("lib") == "LineFault" for model in generated_models)


def test_line_fault_fallback_splits_iidm_and_uses_node_fault(tmp_path: Path) -> None:
    """Split a line and generate a node fault when LineFault is unavailable.

    :param tmp_path: Temporary directory provided by pytest.
    :return: Return value.
    """
    fault_file: Path = tmp_path / "line1-2.json"
    fault_data: Dict[str, object] = make_line_fault("line1-2", ("BUS    1", "BUS    2"), "1-2")
    disconnections: object = fault_data["disconnections"]
    assert isinstance(disconnections, list)
    disconnections[0]["time"] = 10.25
    fault_file.write_text(
        json.dumps(fault_data),
        encoding="utf-8",
    )
    generated_folders: list[str] = prepare_dynawo_line_fault_cases(
        jobs_file=str(DYNAWO_DIR / "IEEE14_JOBS.xml"),
        fault_files=str(fault_file),
        output_dir=str(tmp_path / "generated"),
        line_fault_model_available=False,
    )

    case_dir: Path = Path(generated_folders[0])
    assert 'xmlns="http://www.itesla_project.eu/schema/iidm/1_0"' in (case_dir / "IEEE14_IIDM.xml").read_text()
    generated_iidm: ET.Element = ET.parse(case_dir / "IEEE14_IIDM.xml").getroot()
    generated_lines: list[ET.Element] = [
        line for line in generated_iidm.iter() if line.tag.rsplit("}", 1)[-1] == "line"
    ]
    split_lines: list[ET.Element] = [line for line in generated_lines if "FICT_LINE_line1_2" in line.get("id", "")]
    assert len(split_lines) == 2
    assert not any(line.get("id") == "_BUS____1-BUS____2-1_AC" for line in generated_lines)
    original_line: ET.Element = next(
        line for line in ET.parse(DYNAWO_DIR / "IEEE14_IIDM.xml").getroot().iter()
        if line.get("id") == "_BUS____1-BUS____2-1_AC"
    )
    assert abs(sum(float(line.get("r", "0")) for line in split_lines) - float(original_line.get("r", "0"))) < 1e-8
    generated_models: list[ET.Element] = list(ET.parse(case_dir / "IEEE14_DYD.xml").getroot())
    assert any(model.get("lib") == "NodeFault" for model in generated_models)
    assert any(model.get("var2") == "FICT_BUS_line1_2_ACPIN" for model in generated_models)
    assert all(model.get("staticId") is None for model in generated_models if model.get("lib") == "NodeFault")
    assert not any(model.get("lib") == "LineFault" for model in generated_models)
    assert sum(model.get("lib") == "EventQuadripoleDisconnection" for model in generated_models) == 2
    assert sum(model.get("var1") == "event_state1" for model in generated_models) == 2
    generated_parameters: ET.Element = ET.parse(case_dir / "fault_line1-2.par").getroot()
    assert sum(item.get("name") == "event_disconnectOrigin" for item in generated_parameters.iter()) == 2
    assert sum(item.get("name") == "event_disconnectExtremity" for item in generated_parameters.iter()) == 2
    assert sum(item.get("name") == "event_tEvent" and item.get("value") == "10.25"
               for item in generated_parameters.iter()) == 2
    network_parameters: ET.Element = ET.parse(case_dir / "IEEE14_PAR.xml").getroot()
    assert any(item.get("name") == "FICT_BUS_line1_2_hasShortCircuitCapabilities" and item.get("value") == "true"
               for item in network_parameters.iter())
    direct_cases: list[str] = prepare_dynawo_line_fault_cases(
        jobs_file=str(DYNAWO_DIR / "IEEE14_JOBS.xml"), fault_files=str(fault_file),
        output_dir=str(tmp_path / "direct"),
    )
    direct_parameters: ET.Element = ET.parse(Path(direct_cases[0]) / "fault_line1-2.par").getroot()
    assert any(item.get("name") == "event_tEvent" and item.get("value") == "10.25"
               for item in direct_parameters.iter())


def test_generated_line_fault_runs_in_dynawo(tmp_path: Path) -> None:
    """Run a generated line-fault fallback with the installed Dynawo launcher.

    :param tmp_path: Temporary directory provided by pytest.
    :return: None.
    """
    dynawo: str | None = shutil.which("dynawo")
    if dynawo is None:
        pytest.skip("Dynawo launcher not found on PATH")
    else:
        pass
    version: subprocess.CompletedProcess[str] = subprocess.run(
        [dynawo, "version"], capture_output=True, text=True, timeout=30, check=True,
    )
    if not version.stdout.strip().startswith("1.8."):
        pytest.skip("The runtime fixture is validated with Dynawo 1.8")
    else:
        pass
    case_dir: Path = tmp_path / "base"
    shutil.copytree(TESTS_DIR / "data" / "dynawo_success_case" / "inputs", case_dir,
                    ignore=shutil.ignore_patterns("outputs"))
    dyd_file: Path = case_dir / "IEEE14.dyd"
    dyd_text: str = re.sub(r'(var1="(?:omega_grp|omegaRef_grp|numcc_node|running_grp)_\d+)(")',
                           r'\1_\2', dyd_file.read_text())
    dyd_file.write_text(dyd_text)
    dyd_tree: ET.ElementTree = ET.parse(dyd_file)
    dyd_root: ET.Element = dyd_tree.getroot()
    for element in list(dyd_root):
        if "FAULT_GEN_2" in (element.get("id"), element.get("id1"), element.get("id2")):
            dyd_root.remove(element)
        else:
            pass
    dyd_tree.write(dyd_file, encoding="utf-8", xml_declaration=True)
    fault_file: Path = tmp_path / "fault.json"
    fault_file.write_text(json.dumps(make_line_fault("line1-2", ("BUS    1", "BUS    2"), "1-2")))
    generated: list[str] = prepare_dynawo_line_fault_cases(
        jobs_file=str(case_dir / "IEEE14.jobs"), fault_files=str(fault_file),
        output_dir=str(tmp_path / "generated"), line_fault_model_available=False,
    )
    result: subprocess.CompletedProcess[str] = subprocess.run(
        [dynawo, "jobs", str(Path(generated[0]) / "IEEE14.jobs")], capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert (Path(generated[0]) / "outputs" / "logs" / "dynawo.log").is_file()
    for fault_type in ("node", "transformer"):
        target: Dict[str, object] = {"bus": "BUS    4", "static_id": "_BUS____4_TN",
                                     "terminal_1": "_BUS____4_TN"}
        if fault_type == "transformer":
            target["transformer_id"] = "_BUS____4-BUS____9-1_PT"
        else:
            pass
        fault_data: Dict[str, object] = {
            "fault_id": fault_type, "fault_type": fault_type, "target": target,
            "impedance": {"r": 0.0, "x": 0.0}, "start_time": 10.0, "end_time": 10.1,
            "disconnections": [{"first_bus": "BUS    4", "second_bus": "BUS    9", "parallel_id": "1",
                                "static_id": "_BUS____4-BUS____9-1_PT", "time": 10.1}],
        }
        fault_file.write_text(json.dumps(fault_data))
        generated = prepare_dynawo_line_fault_cases(
            jobs_file=str(case_dir / "IEEE14.jobs"), fault_files=str(fault_file),
            output_dir=str(tmp_path / "generated"),
        )
        result = subprocess.run(
            [dynawo, "jobs", str(Path(generated[0]) / "IEEE14.jobs")], capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, result.stderr


def test_multiple_jobs_mode_writes_per_fault_dyd_par_and_dispatcher(tmp_path: Path) -> None:
    """Generate one `.multiple` dispatcher for a folder of fault plans.

    :param tmp_path: Temporary directory provided by pytest.
    :return: Return value.
    """
    fault_dir: Path = tmp_path / "faults"
    fault_dir.mkdir()
    for fault_id, buses, suffix in (
        ("line1-2", ("BUS    1", "BUS    2"), "1-2"),
        ("line1-5", ("BUS    1", "BUS    5"), "1-5"),
    ):
        fault_file: Path = fault_dir / f"{fault_id}.json"
        fault_file.write_text(json.dumps(make_line_fault(fault_id, buses, suffix)), encoding="utf-8")
    generated_folders: list[str] = prepare_dynawo_line_fault_cases(
        jobs_file=str(DYNAWO_DIR / "IEEE14_JOBS.xml"),
        fault_files=str(fault_dir),
        output_dir=str(tmp_path / "generated"),
        use_multiple_jobs=True,
    )

    assert len(generated_folders) == 1
    case_dir: Path = Path(generated_folders[0])
    multiple_file: Path = case_dir / "IEEE14_JOBS.multiple"
    assert multiple_file.is_file()
    multiple_scenarios: list[ET.Element] = [
        element for element in ET.parse(multiple_file).getroot().iter()
        if element.tag.rsplit("}", 1)[-1] == "scenario"
    ]
    assert len(multiple_scenarios) == 2
    assert (case_dir / "IEEE14_JOBS_line1-2.dyd").is_file()
    assert (case_dir / "IEEE14_JOBS_line1-2.par").is_file()
    assert (case_dir / "IEEE14_JOBS_line1-5.dyd").is_file()
    assert (case_dir / "IEEE14_JOBS_line1-5.par").is_file()


def test_multiple_line_fallback_cases_keep_separate_iidm(tmp_path: Path) -> None:
    """Keep each fault split in its own IIDM and reject a shared dispatcher.

    :param tmp_path: Temporary directory provided by pytest.
    :return: None.
    """
    fault_dir: Path = tmp_path / "faults"
    fault_dir.mkdir()
    for fault_id, buses, suffix in (("line1-2", ("BUS    1", "BUS    2"), "1-2"),
                                    ("line1-5", ("BUS    1", "BUS    5"), "1-5")):
        (fault_dir / f"{fault_id}.json").write_text(json.dumps(make_line_fault(fault_id, buses, suffix)))
    with pytest.raises(ValueError, match="share one IIDM"):
        prepare_dynawo_line_fault_cases(
            jobs_file=str(DYNAWO_DIR / "IEEE14_JOBS.xml"), fault_files=str(fault_dir),
            output_dir=str(tmp_path / "batch"), line_fault_model_available=False, use_multiple_jobs=True,
        )
    generated: list[str] = prepare_dynawo_line_fault_cases(
        jobs_file=str(DYNAWO_DIR / "IEEE14_JOBS.xml"), fault_files=str(fault_dir),
        output_dir=str(tmp_path / "isolated"), line_fault_model_available=False,
    )
    assert len(generated) == 2
    for fault_id in ("line1-2", "line1-5"):
        iidm: str = (tmp_path / "isolated" / fault_id / "IEEE14_IIDM.xml").read_text()
        assert f"FICT_BUS_{fault_id.replace('-', '_')}" in iidm
        assert iidm.count("<substation id=\"FICT_SS_") == 1


def test_ieee14_v2_fault_json_parses_to_line_events(tmp_path: Path) -> None:
    """Parse a single line fault without requiring a plan or a static fixture JSON.

    :param tmp_path: Temporary directory provided by pytest.
    :return: Return value.
    """
    fault_file: Path = tmp_path / "line1-2.json"
    fault_file.write_text(
        json.dumps(make_line_fault("line1-2", ("BUS    1", "BUS    2"), "1-2")),
        encoding="utf-8",
    )

    fault_events = parse_dynawo_fault_json(fault_file)

    assert fault_events.name == "line1-2"
    assert len(fault_events.failure_events) == 1
    assert len(fault_events.mitigation_events) == 3


def test_line_fault_derives_default_disconnection_from_iidm(tmp_path: Path) -> None:
    """Derive the faulted line trip when JSON supplies one common time.

    :param tmp_path: Temporary directory provided by pytest.
    :return: Return value.
    """
    fault_data: Dict[str, object] = make_line_fault("line1-2", ("BUS    1", "BUS    2"), "1-2")
    fault_data.pop("disconnections")
    fault_data["disconnection_time"] = 10.1
    fault_file: Path = tmp_path / "line1-2.json"
    fault_file.write_text(json.dumps(fault_data), encoding="utf-8")
    generated_folders: list[str] = prepare_dynawo_line_fault_cases(
        jobs_file=str(DYNAWO_DIR / "IEEE14_JOBS.xml"),
        fault_files=str(fault_file),
        output_dir=str(tmp_path / "generated"),
    )

    fault_events = parse_dynawo_fault_json(fault_file, DYNAWO_DIR / "IEEE14_IIDM.xml")
    assert len(fault_events.mitigation_events) == 3
    generated_par: ET.Element = ET.parse(Path(generated_folders[0]) / "fault_line1-2.par").getroot()
    assert sum(item.get("name") == "event_tEvent" for item in generated_par.iter()) == 1


def test_automatic_disconnection_rejects_unsupported_topology(tmp_path: Path) -> None:
    """Require explicit trips when protection cannot be inferred safely.

    :param tmp_path: Temporary directory provided by pytest.
    :return: None.
    """
    iidm_file: Path = tmp_path / "case.iidm"
    iidm_file.write_text('<network><substation><voltageLevel topologyKind="BUS_BREAKER">'
                         '<busBreakerTopology><switch id="breaker"/></busBreakerTopology>'
                         '</voltageLevel></substation></network>')
    with pytest.raises(ValueError, match="switches require explicit"):
        derive_default_disconnections(iidm_file, "line", dict(static_id="line"), 1.0)
    with pytest.raises(ValueError, match="Node faults require explicit"):
        derive_default_disconnections(iidm_file, "node", dict(static_id="bus"), 1.0)


@pytest.mark.parametrize(
    ("fault_id", "fault_type", "target", "disconnections", "expected_library"),
    (
        (
            "node_2",
            "node",
            {"bus": "BUS    2", "static_id": "_BUS____2_TN", "terminal_1": "_BUS____2_TN"},
            [{"first_bus": "BUS    1", "second_bus": "BUS    2", "parallel_id": "1",
              "static_id": "_BUS____1-BUS____2-1_AC", "time": 10.1}],
            "NodeFault",
        ),
        (
            "transformer_4_9",
            "transformer",
            {"bus": "BUS    4", "static_id": "_BUS____4_TN", "terminal_1": "_BUS____4_TN",
             "transformer_id": "_BUS____4-BUS____9-1_PT"},
            [{"first_bus": "BUS    4", "second_bus": "BUS    9", "parallel_id": "1",
              "static_id": "_BUS____4-BUS____9-1_PT", "time": 10.25}],
            "NodeFault",
        ),
    ),
)
def test_ieee14_v2_node_and_transformer_fault_case_generation(
    tmp_path: Path,
    fault_id: str,
    fault_type: str,
    target: Dict[str, object],
    disconnections: list[Dict[str, object]],
    expected_library: str,
) -> None:
    """Generate node or transformer fault models and explicit equipment trips.

    :param tmp_path: Temporary directory provided by pytest.
    :param fault_id: Scenario identifier.
    :param fault_type: Fault kind supplied in the JSON plan.
    :param target: Fault target details.
    :param disconnections: Equipment trips requested after fault clearance.
    :param expected_library: Dynawo fault model expected in generated DYD.
    :return: Return value.
    """
    fault_data: Dict[str, object] = {
        "fault_id": fault_id,
        "fault_type": fault_type,
        "target": target,
        "impedance": {"r": 0.0, "x": 0.0},
        "start_time": 10.0,
        "end_time": 10.1,
        "disconnections": disconnections,
    }
    fault_file: Path = tmp_path / f"{fault_id}.json"
    fault_file.write_text(json.dumps(fault_data), encoding="utf-8")
    generated_folders: list[str] = prepare_dynawo_line_fault_cases(
        jobs_file=str(DYNAWO_DIR / "IEEE14_JOBS.xml"),
        fault_files=str(fault_file),
        output_dir=str(tmp_path / "generated"),
    )

    assert len(generated_folders) == 1
    generated_dyd: Path = Path(generated_folders[0]) / "IEEE14_DYD.xml"
    generated_par: Path = Path(generated_folders[0]) / f"fault_{fault_id}.par"
    generated_models: list[ET.Element] = list(ET.parse(generated_dyd).getroot())
    generated_parameters: list[ET.Element] = list(ET.parse(generated_par).getroot())
    assert any(model.get("lib") == expected_library for model in generated_models)
    assert any(model.get("lib") == "EventQuadripoleDisconnection" for model in generated_models)
    assert any(parameter.get("name") == "fault_tBegin" for parameter in generated_parameters[0])
    assert any(parameter.get("name") == "event_tEvent" and parameter.get("value") == str(disconnections[0]["time"])
               for parameter_set in generated_parameters for parameter in parameter_set)


def test_default_workflow_plan_is_built_in_memory() -> None:
    """Expose the default plan for examples that do not have a plan JSON.

    :return: Return value.
    """
    execution_plan: ExecutionPlan = default_execution_plan()

    assert len(execution_plan) == 3
    assert execution_plan.nodes[0].node_type == "CriticalClustersIdentifier"
    assert execution_plan.nodes[1].node_type == "CriticalClustersEvaluator"
    assert execution_plan.nodes[2].node_type == "CriticalClusterSelector"


def test_ieee14_v2_dynawo_json_eeac_when_pypowsybl_is_installed(tmp_path: Path) -> None:
    """Run one Dynawo JSON fault through EEAC when the optional parser is installed.

    :param tmp_path: Temporary directory provided by pytest.
    :return: Return value.
    """
    pytest.importorskip("pypowsybl")
    from deeac.IO.arguments_parser import DynawoRunConfiguration
    from deeac.IO.dynawo.parse_dynawo import parse_dynawo_configuration
    from deeac.workflows import run_dynawo_workflow

    config: DynawoRunConfiguration = DynawoRunConfiguration(
        jobs_file=str(DYNAWO_DIR / "IEEE14_JOBS.xml"),
        iidm_file=None,
        dynawo_dyd_file=None,
        dynawo_par_file=None,
        dynawo_dyn_file=None,
        execution_tree_file=None,
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
    network = parse_dynawo_configuration(config)
    line_branch = next(
        branch
        for branch in network.branches
        if "BUS    1" in (branch.first_bus.name, branch.second_bus.name)
        and "BUS    2" in (branch.first_bus.name, branch.second_bus.name)
    )
    first_bus: str = line_branch.first_bus.name
    second_bus: str = line_branch.second_bus.name
    parallel_id: str = next(iter(line_branch.parallel_elements))
    fault_data: Dict[str, object] = {
        "fault_id": "json_line_1_2",
        "fault_type": "line",
        "target": {"first_bus": first_bus, "second_bus": second_bus, "parallel_id": parallel_id},
        "impedance": {"r": 0.0, "x": 0.0},
        "start_time": 10.0,
        "end_time": 10.1,
        "distance": 0.01,
        "disconnections": [
            {"first_bus": first_bus, "second_bus": second_bus, "parallel_id": parallel_id, "time": 10.1}
        ],
    }
    fault_file: Path = tmp_path / "json_line_1_2.json"
    fault_file.write_text(json.dumps(fault_data), encoding="utf-8")

    results = run_dynawo_workflow(config, str(fault_file))

    assert results.get("json_line_1_2") is not None
