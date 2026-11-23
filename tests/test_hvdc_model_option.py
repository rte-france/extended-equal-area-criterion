"""
Tests for the selectable HVDC electrical model.
"""
from pathlib import Path

import numpy as np

from deeac.IO.eurostag.parse_eurostag import parse_eurostag
from deeac.Models.load import Load
from deeac.Models.matrices.admittance_matrix import AdmittanceMatrix
from deeac.Models.network import Network
from deeac.Models.power_electronics_generator import PowerElectronicsGenerator
from deeac.enums import GeneratorElectricalModel, HvdcElectricalModel


def parse_hvdc_example(hvdc_model: HvdcElectricalModel) -> Network:
    """
    Parse the Eurostag HVDC example with a selected HVDC model.

    The fixture is intentionally the public case_3 example because it contains
    two VSC converters and a solved load-flow table. That makes the test useful
    both for the legacy passive-load behaviour and for the new retained
    current-source behaviour.

    :param hvdc_model: HVDC converter model to pass to the parser.
    :return: Parsed network.
    """
    case_dir: Path = Path(__file__).resolve().parents[1] / "examples" / "eurostag_cases" / "case_3---hvdc"
    return parse_eurostag(
        ech_file=str(case_dir / "fech.ech"),
        dta_file=str(case_dir / "fdta.dta"),
        lf_file=str(case_dir / "fech.lf"),
        hvdc_model=hvdc_model,
    )


def test_eurostag_hvdc_default_stays_legacy_load_model() -> None:
    """
    Keep the historical HVDC conversion available as the default option.

    The old path represents Eurostag HVDC converters as ``Load`` objects and
    applies the deeac v1 sign convention in the load-flow step. This test makes
    that default explicit so future work can add richer models without silently
    changing old studies.
    """
    network = parse_hvdc_example(HvdcElectricalModel.LOAD)

    assert isinstance(network.hvdc_map["BUS_E_T1"], Load)
    assert isinstance(network.hvdc_map["BUS_B_TE"], Load)
    assert np.isclose(network.hvdc_map["BUS_E_T1"].active_power, -199.90)
    assert np.isclose(network.hvdc_map["BUS_B_TE"].active_power, 200.00)


def test_eurostag_hvdc_current_model_retains_converter_buses() -> None:
    """
    Model HVDC converters as retained current-source injections when requested.

    The simple #31 model does not introduce DC dynamics. It only changes the AC
    network representation from passive admittances to explicit converter
    current injections, which must then appear in the retained
    power-electronics bus list of the admittance matrix.
    """
    network = parse_hvdc_example(HvdcElectricalModel.CURRENT)

    first_converter = network.hvdc_map["BUS_E_T1"]
    second_converter = network.hvdc_map["BUS_B_TE"]

    assert isinstance(first_converter, PowerElectronicsGenerator)
    assert isinstance(second_converter, PowerElectronicsGenerator)
    assert first_converter.electrical_model == GeneratorElectricalModel.CURRENT
    assert second_converter.electrical_model == GeneratorElectricalModel.CURRENT
    assert first_converter in network.power_electronics_generators
    assert second_converter in network.power_electronics_generators
    assert np.isclose(first_converter.active_power, 199.90)
    assert np.isclose(second_converter.active_power, -200.00)
    admittance_matrix = AdmittanceMatrix(network.buses)
    assert first_converter.bus in admittance_matrix.power_electronics_current_buses
    assert second_converter.bus in admittance_matrix.power_electronics_current_buses
