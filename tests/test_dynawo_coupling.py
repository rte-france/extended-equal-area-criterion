"""
Tests for Dynawo EEAC coupling helpers.
"""

import os
from pathlib import Path

import pytest

from deeac.DynawoPostProcess.coupling import (
    DynawoCaseCoupler,
    DynawoCaseGenerationStatus,
    DynawoFaultSelectionOptions,
)
from deeac.DynawoPostProcess.runner import (
    DynawoBinaryOptions,
    DynawoOperatingSystem,
    resolve_dynawo_binary_path,
)
from deeac.IO.arguments_parser import DynawoRunConfiguration
from deeac.Simulations.results import EEACResult, EEACResults
from deeac.enums import OMIBStabilityState


def get_ieee14_dynawo_dir() -> str:
    """
    Return the IEEE14 Dynawo fixture directory.

    :return: Fixture directory path.
    """
    tests_dir: str = os.path.dirname(__file__)
    ieee14_dir: str = os.path.join(tests_dir, "data", "IEEE14")
    dynawo_dir: str = os.path.join(ieee14_dir, "Dynawo")
    return dynawo_dir


def get_repo_root_dir() -> str:
    """
    Return repository root directory.

    :return: Repository root directory.
    """
    tests_dir: str = os.path.dirname(__file__)
    repo_root_dir: str = os.path.abspath(os.path.join(tests_dir, ".."))
    return repo_root_dir


def get_deeac_dynawo_root_dir() -> str:
    """
    Return local Dynawo install root.

    :return: Local Dynawo install root.
    """
    repo_root_dir: str = get_repo_root_dir()
    deeac_dynawo_root_dir: str = os.path.join(repo_root_dir, "Dynawo_Linux_v1.7.0")
    return deeac_dynawo_root_dir


def is_local_dynawo_detected() -> bool:
    """
    Tell whether the local Dynawo test installation is currently present.

    :return: ``True`` when the local Dynawo installation can be detected.
    """
    dynawo_root_dir: str = get_deeac_dynawo_root_dir()
    dynawo_install_dir: str = os.path.join(dynawo_root_dir, "dynawo")
    dynawo_binary_candidates: list[str] = list()
    dynawo_binary_candidates.append(os.path.join(dynawo_install_dir, "bin", "dynawo"))
    dynawo_binary_candidates.append(os.path.join(dynawo_install_dir, "bin", "dynawo-1.7.0"))
    if os.path.isdir(dynawo_install_dir):
        pass
    else:
        return False
    for candidate in dynawo_binary_candidates:
        if os.path.isfile(candidate):
            return True
        else:
            pass
    return False


def get_ieee14_plan_path() -> str:
    """
    Return the IEEE14 execution plan path.

    :return: Execution plan path.
    """
    tests_dir: str = os.path.dirname(__file__)
    ieee14_dir: str = os.path.join(tests_dir, "data", "IEEE14")
    plan_path: str = os.path.join(ieee14_dir, "branch_1.json")
    return plan_path


def build_dynawo_config() -> DynawoRunConfiguration:
    """
    Build a Dynawo run configuration for the IEEE14 test fixture.

    :return: Dynawo run configuration.
    """
    dynawo_dir: str = get_ieee14_dynawo_dir()
    plan_path: str = get_ieee14_plan_path()
    config = DynawoRunConfiguration(
        jobs_file=os.path.join(dynawo_dir, "IEEE14.jobs"),
        iidm_file=None,
        dynawo_dyd_file=None,
        dynawo_par_file=None,
        dynawo_dyn_file=None,
        execution_tree_file=plan_path,
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
    return config


def build_eeac_results() -> EEACResults:
    """
    Build synthetic EEAC results for filtering and generation tests.

    :return: EEAC results.
    """
    results = EEACResults()
    # This fault exists in IEEE14.dyd and should be generated.
    results.add(
        "line1_5",
        EEACResult(
            status=OMIBStabilityState.ALWAYS_UNSTABLE.value,
            swing_state="FORWARD",
            cct=None,
        ),
    )
    # This fault is intentionally absent in IEEE14.dyd and should be skipped.
    results.add(
        "line1_2",
        EEACResult(
            status=OMIBStabilityState.POTENTIALLY_STABLE.value,
            swing_state="FORWARD",
            cct=0.25,
        ),
    )
    return results


def test_dynawo_case_generation_from_eeac_selection(tmp_path: Path) -> None:
    """
    Generate Dynawo files from selected EEAC results and verify output files.

    :param tmp_path: Pytest temporary path fixture.
    :return: Return value.
    """
    config = build_dynawo_config()
    eeac_results = build_eeac_results()
    selection_options = DynawoFaultSelectionOptions(
        statuses=[OMIBStabilityState.ALWAYS_UNSTABLE, OMIBStabilityState.POTENTIALLY_STABLE],
        cct_min=0.2,
        cct_max=0.3,
    )
    coupler = DynawoCaseCoupler(
        run_configuration=config,
        eeac_results=eeac_results,
        selection_options=selection_options,
    )

    report = coupler.generate_cases(str(tmp_path), rewrite=True)

    by_name = dict()
    for entry in report.entries:
        by_name[entry.fault_name] = entry

    # line1_5 is ALWAYS_UNSTABLE with no CCT; with CCT bounds it should be filtered out.
    assert "line1_5" not in by_name
    assert "line1_2" in by_name
    assert by_name["line1_2"].generation_status == DynawoCaseGenerationStatus.SKIPPED

    selection_without_cct = DynawoFaultSelectionOptions(
        statuses=[OMIBStabilityState.ALWAYS_UNSTABLE],
        cct_min=None,
        cct_max=None,
    )
    coupler_without_cct = DynawoCaseCoupler(
        run_configuration=config,
        eeac_results=eeac_results,
        selection_options=selection_without_cct,
    )
    report_without_cct = coupler_without_cct.generate_cases(str(tmp_path / "no_cct"), rewrite=True)
    by_name_without_cct = dict()
    for entry in report_without_cct.entries:
        by_name_without_cct[entry.fault_name] = entry

    assert "line1_5" in by_name_without_cct
    generated_entry = by_name_without_cct["line1_5"]
    assert generated_entry.generation_status == DynawoCaseGenerationStatus.GENERATED
    assert generated_entry.jobs_file is not None
    assert generated_entry.dyd_file is not None
    assert generated_entry.par_file is not None
    assert generated_entry.output_dir is not None
    assert os.path.exists(generated_entry.jobs_file)
    assert os.path.exists(generated_entry.dyd_file)
    assert os.path.exists(generated_entry.par_file)
    assert os.path.isdir(generated_entry.output_dir)

    jobs_text = Path(generated_entry.jobs_file).read_text(encoding="utf-8")
    dyd_text = Path(generated_entry.dyd_file).read_text(encoding="utf-8")
    par_text = Path(generated_entry.par_file).read_text(encoding="utf-8")
    assert "fault_case.dyd" in jobs_text
    assert 'inputFile="IEEE14.crv"' not in jobs_text
    assert "LineFault" in dyd_text
    assert "line_switchOffSignal1_value" in dyd_text
    assert "line_tBegin" in par_text
    assert "line_tEnd" in par_text


def test_resolve_dynawo_binary_path_linux_from_install_root() -> None:
    """
    Resolve Dynawo binary from Linux install-root fixture.

    :return: Return value.
    """
    if is_local_dynawo_detected():
        pass
    else:
        pytest.skip("Local Dynawo installation not detected.")
    options = DynawoBinaryOptions(
        install_root_dir=get_deeac_dynawo_root_dir(),
        install_dir=None,
        binary_path=None,
        operating_system=DynawoOperatingSystem.LINUX,
    )
    resolved_binary_path: str = resolve_dynawo_binary_path(options)
    assert os.path.exists(resolved_binary_path)
    assert os.path.isfile(resolved_binary_path)
    assert os.path.basename(resolved_binary_path) in {"dynawo", "dynawo-1.7.0", "dynawo.exe"}


def test_resolve_dynawo_binary_path_explicit_path() -> None:
    """
    Resolve Dynawo binary when explicit path is provided.

    :return: Return value.
    """
    if is_local_dynawo_detected():
        pass
    else:
        pytest.skip("Local Dynawo installation not detected.")
    explicit_path: str = os.path.join(get_deeac_dynawo_root_dir(), "dynawo", "bin", "dynawo-1.7.0")
    options = DynawoBinaryOptions(
        install_root_dir=None,
        install_dir=None,
        binary_path=explicit_path,
        operating_system=None,
    )
    resolved_binary_path: str = resolve_dynawo_binary_path(options)
    assert resolved_binary_path == explicit_path
