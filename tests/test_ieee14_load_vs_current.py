"""
Integration tests for the IEEE14 load-vs-current renewable modeling dataset.
"""

import csv
from pathlib import Path
from typing import List, Optional

import pytest

from deeac.IO.arguments_parser import EurostagRunConfiguration
from deeac.Simulations.results import EEACResult
from deeac.enums import GeneratorElectricalModel
from deeac.main import deeac_eurostag

TESTS_DIR: Path = Path(__file__).resolve().parent
IEEE14_LOAD_VS_CURRENT_DIR: Path = TESTS_DIR / "data" / "ieee14_load_vs_current"
IEEE14_CASE_DIR: Path = IEEE14_LOAD_VS_CURRENT_DIR / "IEEE14"
IEEE14_RESULTS_CSV_PATH: Path = IEEE14_LOAD_VS_CURRENT_DIR / "IEEE14_experiments.csv"


class IEEE14LoadVsCurrentExpectation:
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
        Initialize one expected IEEE14 experiment row.

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


def load_ieee14_load_vs_current_expectations(csv_path: Path) -> List[IEEE14LoadVsCurrentExpectation]:
    """
    Load expected IEEE14 experiments from the reference CSV file.

    :param csv_path: Path to the CSV file containing the Load and Current column expectations.
    :return: Ordered list of expected experiments.
    :rtype: List[IEEE14LoadVsCurrentExpectation]
    """
    expectations: List[IEEE14LoadVsCurrentExpectation] = list()

    # The CSV file is the single source of truth for the expected CCT values.
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
                                    IEEE14LoadVsCurrentExpectation(
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


def build_ieee14_load_vs_current_configuration(
    expectation: IEEE14LoadVsCurrentExpectation,
    ren_model: GeneratorElectricalModel,
) -> EurostagRunConfiguration:
    """
    Build a direct Eurostag EEAC configuration for one IEEE14 study.

    :param expectation: One expected IEEE14 experiment entry.
    :param ren_model: Renewable-generator electrical model used for the run.
    :return: Configured Eurostag run configuration.
    :rtype: EurostagRunConfiguration
    """
    seq_path: Path = IEEE14_CASE_DIR / f"{expectation.fault_name}.seq"

    # The test builds the typed configuration directly so it exercises the real Eurostag code path.
    return EurostagRunConfiguration(
        ech_file=str(IEEE14_CASE_DIR / "ech" / f"{expectation.case_name}.ech"),
        dta_file=str(IEEE14_CASE_DIR / "fdta.dta"),
        lf_file=str(IEEE14_CASE_DIR / "lf" / f"{expectation.case_name}.lf"),
        execution_tree_file=str(IEEE14_CASE_DIR / "branch_1.json"),
        execution_tree=None,
        seq_file=str(seq_path),
        seq_file_folder=str(IEEE14_CASE_DIR),
        seq_files=[str(seq_path)],
        island_threshold=0.0,
        cores=1,
        protection_delay=15.0,
        ren_model=ren_model,
        verbose=False,
        output_dir=None,
        json_path=None,
        rewrite=True,
        warn=False,
    )


def get_expected_cct_ms(
    expectation: IEEE14LoadVsCurrentExpectation,
    ren_model: GeneratorElectricalModel,
) -> int:
    """
    Get the expected CCT in milliseconds for one renewable model.

    :param expectation: One expected IEEE14 experiment entry.
    :param ren_model: Renewable-generator electrical model used for the run.
    :return: Expected CCT in milliseconds.
    :rtype: int
    """
    if ren_model == GeneratorElectricalModel.CURRENT:
        return expectation.expected_current_cct_ms
    else:
        return expectation.expected_load_cct_ms


def get_column_name_for_model(ren_model: GeneratorElectricalModel) -> str:
    """
    Map one renewable model to the expected CSV column label.

    :param ren_model: Renewable-generator electrical model used for the run.
    :return: Expected CSV column label.
    :rtype: str
    """
    if ren_model == GeneratorElectricalModel.CURRENT:
        return "Current"
    else:
        return "Load"


def get_result_cct_ms(result: EEACResult, fault_name: str) -> int:
    """
    Extract the computed CCT from one EEAC result object.

    :param result: EEAC result returned for one fault.
    :param fault_name: Fault name used to make the error message explicit.
    :return: Truncated CCT in milliseconds.
    :rtype: int
    """
    # The dataset defines a concrete CCT for every case, so a missing value is a hard failure.
    if result.cct is not None:
        return int(result.cct * 1000.0)
    else:
        raise ValueError(f"Missing CCT for fault {fault_name}.")


@pytest.mark.parametrize(
    ("ren_model", "expected_column_name"),
    [
        (GeneratorElectricalModel.LOAD, "Load"),
        (GeneratorElectricalModel.CURRENT, "Current"),
    ],
)
def test_ieee14_load_vs_current_reference_matrix(
    ren_model: GeneratorElectricalModel,
    expected_column_name: str,
) -> None:
    """
    Reproduce the IEEE14 Load and Current reference columns with the current EEAC code.

    :param ren_model: Renewable-generator electrical model used for the run.
    :param expected_column_name: Expected CSV column name used only for failure messages.
    :return: Return value.
    """
    expectations: List[IEEE14LoadVsCurrentExpectation] = load_ieee14_load_vs_current_expectations(
        IEEE14_RESULTS_CSV_PATH
    )
    mismatches: List[str] = list()

    # Each expectation is replayed through the current EEAC implementation for the selected renewable model.
    for expectation in expectations:
        config: EurostagRunConfiguration = build_ieee14_load_vs_current_configuration(expectation, ren_model)
        results = deeac_eurostag(config)
        result: Optional[EEACResult] = results.get(expectation.fault_name)

        if result is not None:
            computed_cluster_value: Optional[str] = result.critical_cluster
            computed_cct_ms: int = get_result_cct_ms(result, expectation.fault_name)
            expected_cct_ms: int = get_expected_cct_ms(expectation, ren_model)

            # The dataset checks both the CCT and the selected critical cluster because both are user-visible outputs.
            if computed_cluster_value is not None:
                if computed_cluster_value == expectation.expected_cluster and computed_cct_ms == expected_cct_ms:
                    pass
                else:
                    mismatches.append(
                        f"{ren_model.name} {expectation.fault_name}/{expectation.case_name}: "
                        f"expected cluster {expectation.expected_cluster!r}, got {computed_cluster_value!r}; "
                        f"expected {expected_column_name} CCT {expected_cct_ms} ms, got {computed_cct_ms} ms"
                    )
            else:
                mismatches.append(
                    f"{ren_model.name} {expectation.fault_name}/{expectation.case_name}: missing critical cluster"
                )
        else:
            mismatches.append(
                f"{ren_model.name} {expectation.fault_name}/{expectation.case_name}: missing EEAC result"
            )

    assert len(mismatches) == 0, "\n".join(mismatches)
