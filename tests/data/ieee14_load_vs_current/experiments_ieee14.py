"""
Reproduce the IEEE14 "Load" and "Current" CCT columns with the current EEAC code.

:module: experiments_ieee14
"""

from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from deeac.IO.arguments_parser import EurostagRunConfiguration
from deeac.Simulations.results import EEACResult
from deeac.enums import GeneratorElectricalModel
from deeac.main import deeac_eurostag


class ExperimentExpectation:
    """
    Expected IEEE14 experiment entry loaded from the reference CSV file.

    :ivar fault_name: Sequence file stem used as the fault identifier.
    :ivar expected_cluster: Expected critical cluster name.
    :ivar case_name: ECH and LF file stem used for the experiment.
    :ivar expected_load_cct_ms: Expected CCT in milliseconds from the Load column.
    :ivar expected_current_cct_ms: Expected CCT in milliseconds from the Current column.
    """

    __slots__ = ("fault_name", "expected_cluster", "case_name", "expected_load_cct_ms", "expected_current_cct_ms")

    def __init__(
        self,
        fault_name: str,
        expected_cluster: str,
        case_name: str,
        expected_load_cct_ms: int,
        expected_current_cct_ms: int,
    ) -> None:
        """
        Initialize the expected experiment row.

        :param fault_name: Sequence file stem used as the fault identifier.
        :param expected_cluster: Expected critical cluster name.
        :param case_name: ECH and LF file stem used for the experiment.
        :param expected_load_cct_ms: Expected CCT in milliseconds from the Load column.
        :param expected_current_cct_ms: Expected CCT in milliseconds from the Current column.
        :return: Return value.
        """
        self.fault_name = fault_name
        self.expected_cluster = expected_cluster
        self.case_name = case_name
        self.expected_load_cct_ms = expected_load_cct_ms
        self.expected_current_cct_ms = expected_current_cct_ms


class ExperimentResult:
    """
    One IEEE14 experiment result produced by the current EEAC code.

    :ivar fault_name: Sequence file stem used as the fault identifier.
    :ivar case_name: ECH and LF file stem used for the experiment.
    :ivar expected_cluster: Expected critical cluster name from the CSV file.
    :ivar computed_cluster: Critical cluster returned by the current EEAC code.
    :ivar model_name: Electrical model label used for the run.
    :ivar expected_cct_ms: Expected CCT in milliseconds for the selected model.
    :ivar computed_cct_ms: Computed CCT in milliseconds from the current EEAC code.
    :ivar status: EEAC final status for the fault.
    """

    __slots__ = (
        "model_name",
        "fault_name",
        "case_name",
        "expected_cluster",
        "computed_cluster",
        "expected_cct_ms",
        "computed_cct_ms",
        "status",
    )

    def __init__(
        self,
        model_name: str,
        fault_name: str,
        case_name: str,
        expected_cluster: str,
        computed_cluster: str,
        expected_cct_ms: int,
        computed_cct_ms: int,
        status: str,
    ) -> None:
        """
        Initialize one computed experiment result.

        :param model_name: Electrical model label used for the run.
        :param fault_name: Sequence file stem used as the fault identifier.
        :param case_name: ECH and LF file stem used for the experiment.
        :param expected_cluster: Expected critical cluster name from the CSV file.
        :param computed_cluster: Critical cluster returned by the current EEAC code.
        :param expected_cct_ms: Expected CCT in milliseconds for the selected model.
        :param computed_cct_ms: Computed CCT in milliseconds from the current EEAC code.
        :param status: EEAC final status for the fault.
        :return: Return value.
        """
        self.model_name = model_name
        self.fault_name = fault_name
        self.case_name = case_name
        self.expected_cluster = expected_cluster
        self.computed_cluster = computed_cluster
        self.expected_cct_ms = expected_cct_ms
        self.computed_cct_ms = computed_cct_ms
        self.status = status

    def matches_expectation(self) -> bool:
        """
        Check whether the computed result matches the CSV expectation.

        :return: True when both CCT and critical cluster match the expectation.
        :rtype: bool
        """
        if self.expected_cluster == self.computed_cluster:
            if self.expected_cct_ms == self.computed_cct_ms:
                return True
            else:
                return False
        else:
            return False


def load_expectations(csv_path: Path) -> List[ExperimentExpectation]:
    """
    Load expected IEEE14 experiments from the reference CSV file.

    :param csv_path: Path to the CSV file containing the Load and Current column expectations.
    :return: Ordered list of expected experiments.
    :rtype: List[ExperimentExpectation]
    """
    expectations: List[ExperimentExpectation] = list()

    # The CSV file is the single source of truth for the expected Load and Current values.
    with csv_path.open("r", encoding="utf8", newline="") as file_pointer:
        reader = csv.DictReader(file_pointer)
        for row in reader:
            fault_name_value: Optional[str] = row.get("Fault")
            expected_cluster_value: Optional[str] = row.get("Critical cluster")
            case_name_value: Optional[str] = row.get("Name")
            expected_load_cct_value: Optional[str] = row.get("Load")
            expected_current_cct_value: Optional[str] = row.get("Current")

            # Every required field is checked explicitly so malformed inputs fail early and clearly.
            if fault_name_value is not None:
                if expected_cluster_value is not None:
                    if case_name_value is not None:
                        if expected_load_cct_value is not None:
                            if expected_current_cct_value is not None:
                                expectations.append(
                                    ExperimentExpectation(
                                        fault_name=fault_name_value,
                                        expected_cluster=expected_cluster_value,
                                        case_name=case_name_value,
                                        expected_load_cct_ms=int(expected_load_cct_value),
                                        expected_current_cct_ms=int(expected_current_cct_value),
                                    )
                                )
                            else:
                                raise ValueError(f"Missing Current value in {csv_path}.")
                        else:
                            raise ValueError(f"Missing Load value in {csv_path}.")
                    else:
                        raise ValueError(f"Missing Name value in {csv_path}.")
                else:
                    raise ValueError(f"Missing Critical cluster value in {csv_path}.")
            else:
                raise ValueError(f"Missing Fault value in {csv_path}.")

    return expectations


def cct_seconds_to_milliseconds(cct_seconds: float) -> int:
    """
    Convert a CCT from seconds to truncated milliseconds.

    The historical CSV stores integer milliseconds by truncating the floating-point
    EEAC CCT value rather than rounding it.

    :param cct_seconds: CCT in seconds returned by EEAC.
    :return: Truncated CCT in milliseconds.
    :rtype: int
    """
    return int(cct_seconds * 1000.0)


def extract_result_cct_ms(result: EEACResult, fault_name: str) -> int:
    """
    Extract the computed CCT from one EEAC result object.

    :param result: EEAC result returned for one fault.
    :param fault_name: Fault name used to make the error message explicit.
    :return: Truncated CCT in milliseconds.
    :rtype: int
    """
    # The script reproduces the Load column, so a missing CCT is a hard failure.
    if result.cct is not None:
        return cct_seconds_to_milliseconds(result.cct)
    else:
        raise ValueError(f"Missing CCT for fault {fault_name}.")


def build_eurostag_configuration(
    expectation: ExperimentExpectation,
    ieee14_dir: Path,
    output_root: Path,
    ren_model: GeneratorElectricalModel,
) -> EurostagRunConfiguration:
    """
    Build a direct Eurostag EEAC configuration for one IEEE14 study.

    :param expectation: One expected IEEE14 experiment entry.
    :param ieee14_dir: Directory containing the IEEE14 Eurostag files.
    :param output_root: Temporary output root used by DEEAC.
    :param ren_model: Renewable-generator electrical model used for the run.
    :return: Configured Eurostag run configuration.
    """
    output_dir: Path = output_root / ren_model.name.lower() / expectation.fault_name / expectation.case_name
    seq_path: Path = ieee14_dir / f"{expectation.fault_name}.seq"

    # The config is built explicitly per study so the coding path stays typed and avoids CLI-shaped plumbing.
    return EurostagRunConfiguration(
        ech_file=str(ieee14_dir / "ech" / f"{expectation.case_name}.ech"),
        dta_file=str(ieee14_dir / "fdta.dta"),
        lf_file=str(ieee14_dir / "lf" / f"{expectation.case_name}.lf"),
        execution_tree_file=str(ieee14_dir / "branch_1.json"),
        execution_tree=None,
        seq_file=str(seq_path),
        seq_file_folder=str(ieee14_dir),
        seq_files=[str(seq_path)],
        island_threshold=0.0,
        cores=1,
        protection_delay=15.0,
        ren_model=ren_model,
        verbose=False,
        output_dir=str(output_dir),
        json_path=None,
        rewrite=True,
        warn=False,
    )


def run_one_experiment(
    expectation: ExperimentExpectation,
    ieee14_dir: Path,
    output_root: Path,
    ren_model: GeneratorElectricalModel,
) -> ExperimentResult:
    """
    Run one IEEE14 experiment with the current EEAC implementation.

    :param expectation: One expected IEEE14 experiment entry.
    :param ieee14_dir: Directory containing the IEEE14 Eurostag files.
    :param output_root: Temporary output root used by DEEAC.
    :param ren_model: Renewable-generator electrical model used for the run.
    :return: Computed experiment result.
    :rtype: ExperimentResult
    """
    expected_cct_ms: int = expectation.expected_load_cct_ms
    if ren_model == GeneratorElectricalModel.CURRENT:
        expected_cct_ms = expectation.expected_current_cct_ms
    else:
        expected_cct_ms = expectation.expected_load_cct_ms

    config = build_eurostag_configuration(expectation, ieee14_dir, output_root, ren_model)

    # Running through the typed Eurostag entry point avoids the CLI argument layer while keeping the real EEAC path.
    results = deeac_eurostag(config)
    result: Optional[EEACResult] = results.get(expectation.fault_name)

    # The returned object is validated explicitly so missing results stop the batch immediately.
    if result is not None:
        computed_cluster_value: Optional[str] = result.critical_cluster
        status_value: Optional[str] = result.status
        computed_cct_ms: int = extract_result_cct_ms(result, expectation.fault_name)

        if computed_cluster_value is not None:
            if status_value is not None:
                return ExperimentResult(
                    model_name=ren_model.name,
                    fault_name=expectation.fault_name,
                    case_name=expectation.case_name,
                    expected_cluster=expectation.expected_cluster,
                    computed_cluster=computed_cluster_value,
                    expected_cct_ms=expected_cct_ms,
                    computed_cct_ms=computed_cct_ms,
                    status=status_value,
                )
            else:
                raise ValueError(f"Missing status for fault {expectation.fault_name}.")
        else:
            raise ValueError(f"Missing critical cluster for fault {expectation.fault_name}.")
    else:
        raise ValueError(f"Missing EEAC result for fault {expectation.fault_name}.")


def print_results(results: List[ExperimentResult]) -> None:
    """
    Print the computed IEEE14 results in a compact CSV-like table.

    :param results: Ordered list of computed experiment results.
    :return: Return value.
    """
    print("Model,Fault,Name,ExpectedCluster,ComputedCluster,ExpectedCctMs,ComputedCctMs,Status,Match")
    for result in results:
        match_value: str = "yes"
        if result.matches_expectation():
            match_value = "yes"
        else:
            match_value = "no"

        print(
            f"{result.model_name},{result.fault_name},{result.case_name},{result.expected_cluster},"
            f"{result.computed_cluster},{result.expected_cct_ms},{result.computed_cct_ms},"
            f"{result.status},{match_value}"
        )


def raise_if_mismatch(results: List[ExperimentResult]) -> None:
    """
    Fail when one computed experiment differs from the expected Load column.

    :param results: Ordered list of computed experiment results.
    :return: Return value.
    """
    mismatches: List[ExperimentResult] = list()

    # Mismatches are collected first so the user gets the full picture instead of a stop at the first difference.
    for result in results:
        if result.matches_expectation():
            pass
        else:
            mismatches.append(result)

    if len(mismatches) == 0:
        print(f"All {len(results)} IEEE14 experiments reproduced the expected Load/Current columns.")
    else:
        print(f"{len(mismatches)} IEEE14 experiments did not reproduce the expected Load/Current columns.", file=sys.stderr)
        raise SystemExit(1)


def main() -> None:
    """
    Run the IEEE14 experiment matrix and compare it with the Load and Current columns.

    :return: Return value.
    """
    base_dir: Path = Path(__file__).resolve().parent
    ieee14_dir: Path = base_dir / "IEEE14"
    csv_path: Path = base_dir / "IEEE14_experiments.csv"
    expectations: List[ExperimentExpectation] = load_expectations(csv_path)
    results: List[ExperimentResult] = list()
    ren_models: List[GeneratorElectricalModel] = [
        GeneratorElectricalModel.LOAD,
        GeneratorElectricalModel.CURRENT,
    ]

    # A temporary output root keeps the run reproducible without polluting the tracked IEEE14 output tree.
    with tempfile.TemporaryDirectory(prefix="ieee14_load_") as temporary_directory:
        output_root = Path(temporary_directory)

        # Each CSV row is replayed once per renewable model so both historical columns stay checked together.
        for ren_model in ren_models:
            for expectation in expectations:
                result = run_one_experiment(expectation, ieee14_dir, output_root, ren_model)
                results.append(result)

    # The final report is printed before the status check so successful and failed runs expose the same data.
    print_results(results)
    raise_if_mismatch(results)


if __name__ == "__main__":
    main()
