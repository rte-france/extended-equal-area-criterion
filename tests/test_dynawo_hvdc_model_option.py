"""
Tests for PowSyBl/Dynawo HVDC model selection.
"""
from pathlib import Path

import numpy as np
import pypowsybl as pp

from deeac.IO.dynawo.dynawo_parser import IidmParser
from deeac.Models.load import Load
from deeac.Models.network import Network
from deeac.Models.power_electronics_generator import PowerElectronicsGenerator
from deeac.enums import GeneratorElectricalModel, HvdcElectricalModel


def write_powsybl_hvdc_case(tmp_path: Path) -> Path:
    """
    Write a real PowSyBl sample network containing IIDM HVDC lines.

    The built-in four-substation node-breaker sample is deliberately used
    instead of a mock because it exercises the same PowSyBl dataframes that the
    Dynawo parser consumes in production:

    * ``get_hvdc_lines`` for link-level target powers.
    * ``get_vsc_converter_stations`` and ``get_lcc_converter_stations`` for
      resolving converter station ids to AC bus ids.

    :param tmp_path: Pytest temporary directory.
    :return: Path to the exported XIIDM fixture.
    """
    network = pp.network.create_four_substations_node_breaker_network()
    iidm_path: Path = tmp_path / "four_substations_hvdc.xiidm"
    network.save(iidm_path)
    return iidm_path


def parse_powsybl_hvdc_case(tmp_path: Path, hvdc_model: HvdcElectricalModel) -> Network:
    """
    Parse the real PowSyBl HVDC fixture through ``IidmParser``.

    :param tmp_path: Pytest temporary directory.
    :param hvdc_model: HVDC model selected for parser compilation.
    :return: Parsed DEEAC network.
    """
    iidm_path: Path = write_powsybl_hvdc_case(tmp_path)
    parser = IidmParser(str(iidm_path), hvdc_model=hvdc_model)
    return parser.parse()


def test_dynawo_powsybl_hvdc_default_stays_legacy_load_model(tmp_path: Path) -> None:
    """
    Keep the historical PowSyBl HVDC conversion as the default.

    Before #31, the Dynawo/PowSyBl path represented each HVDC line as one load
    on converter station 2. This test uses a real PowSyBl HVDC sample so that
    the compatibility check covers converter-station bus resolution as well as
    the final numerical object type.

    :param tmp_path: Pytest temporary directory.
    :return: Return value.
    """
    network: Network = parse_powsybl_hvdc_case(tmp_path, HvdcElectricalModel.LOAD)

    assert set(network.hvdc_map.keys()) == {"HVDC1", "HVDC2"}
    assert isinstance(network.hvdc_map["HVDC1"], Load)
    assert isinstance(network.hvdc_map["HVDC2"], Load)
    assert network.hvdc_map["HVDC1"].bus.name == "S2VL1_0"
    assert network.hvdc_map["HVDC2"].bus.name == "S3VL1_0"
    assert np.isclose(network.hvdc_map["HVDC1"].active_power, 10.0)
    assert np.isclose(network.hvdc_map["HVDC2"].active_power, 80.0)


def test_dynawo_powsybl_hvdc_current_model_uses_endpoint_injections(tmp_path: Path) -> None:
    """
    Compile PowSyBl HVDC lines into endpoint current injections when requested.

    The sample contains one VSC HVDC line and one LCC HVDC line. Current-source
    mode must therefore produce two retained converter injections per HVDC
    line, using equal-and-opposite active powers from the PowSyBl ``target_p``
    value.

    :param tmp_path: Pytest temporary directory.
    :return: Return value.
    """
    network: Network = parse_powsybl_hvdc_case(tmp_path, HvdcElectricalModel.CURRENT)

    assert set(network.hvdc_map.keys()) == {"VSC1", "VSC2", "LCC1", "LCC2"}

    expected_active_powers = dict()
    expected_active_powers["VSC1"] = -10.0
    expected_active_powers["VSC2"] = 10.0
    expected_active_powers["LCC1"] = -80.0
    expected_active_powers["LCC2"] = 80.0

    for converter_name, expected_active_power in expected_active_powers.items():
        converter = network.hvdc_map[converter_name]
        assert isinstance(converter, PowerElectronicsGenerator)
        assert converter.electrical_model == GeneratorElectricalModel.CURRENT
        assert np.isclose(converter.active_power, expected_active_power)
        assert converter in network.power_electronics_generators
        assert converter in converter.bus.power_electronics_generators
