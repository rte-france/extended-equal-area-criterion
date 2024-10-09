# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest
import math
from typing import List, Dict

from tests import TEST_DATA_FOLDER
from deeac.adapters.topology.eurostag.dtos import (
    State, TransformerRegulatingMode, GeneratorDynamicPart, GeneratorRegulatingMode, NetworkParameters, Node, Line,
    CouplingDevice, Type1Transformer, Type8Transformer, TransformerTap, Load, GeneratorStaticPart, SlackBus,
    NetworkData, CouplingDeviceOpeningCode, CapacitorBank, StaticVarCompensator, HVDCCurrentSourceConverter,
    HVDCVoltageSourceConverter, HVDCConverterState
)
from deeac.adapters.topology.eurostag import RecordDescription, NetworkDataDescription, EurostagTopologyParser
from deeac.adapters.topology.eurostag.ech_file_parser import EchEurostagFileParser, ECH_FILE_DESCRIPTION, EchRecordType
from deeac.adapters.topology.eurostag.dta_file_parser import DtaEurostagFileParser, DTA_FILE_DESCRIPTION, DtaRecordType
from deeac.domain.ports.dtos import Value, Unit
from deeac.domain.ports.dtos import topology as topology_dtos


@pytest.fixture
def first_cd_record() -> str:
    return "6 NODE23  -NODE2409A       0.       0."


@pytest.fixture
def second_cd_record() -> str:
    return "6 NODE23   NODE2409A       0.       0."


@pytest.fixture
def invalid_cd_record() -> str:
    return "6 NODE23  -NODE2409A"


@pytest.fixture
def invalid_data_format_cd_record() -> str:
    return "6         +NODE2409A       0.       0."


@pytest.fixture
def not_of_interest_record() -> str:
    return "NI 876       0.       0."


@pytest.fixture
def tfo8_records() -> List[str]:
    return [
        "48NHVA1    NHVA2   1    1000.    0.21     0.02     0.09       7.       0.       0.",
        "48                      0    0                                     N",
        "48                    -10     400.     400.      10.     -20.",
        "48                      0     400.     400.      10.       0."
    ]


@pytest.fixture
def dyn_gen_records() -> List[str]:
    return [
        "M2       S         0.       0.",
        "GENA1                1150.      24.                         0.      6.3",
        "            0.004    0.219     2.57    0.420      0.3    7.695    0.061",
        "                               2.57    0.662    0.301    0.643    0.095 1 4      2",
        "        N                                                1000.    1100.",
        "              0.1    6.025      0.1    6.025"
    ]


@pytest.fixture
def cd_record_description() -> RecordDescription:
    return ECH_FILE_DESCRIPTION[EchRecordType.COUPLING_DEVICE].record_descriptions[0]


@pytest.fixture
def cd_network_data_description() -> NetworkDataDescription:
    return ECH_FILE_DESCRIPTION[EchRecordType.COUPLING_DEVICE]


@pytest.fixture
def tfo8_network_data_description() -> NetworkDataDescription:
    return ECH_FILE_DESCRIPTION[EchRecordType.TYPE8_TRANSFORMER]


@pytest.fixture
def dyn_gen_network_data_description() -> NetworkDataDescription:
    return DTA_FILE_DESCRIPTION[DtaRecordType.FULL_EXTERNAL_PARAM_GENERATOR]


@pytest.fixture
def cd_open_network_data() -> CouplingDevice:
    return CouplingDevice(
        sending_node="NODE23",
        receiving_node="NODE2409",
        opening_code=CouplingDeviceOpeningCode.OPEN,
        parallel_index="A"
    )


@pytest.fixture
def cd_closed_network_data() -> CouplingDevice:
    return CouplingDevice(
        sending_node="NODE23",
        receiving_node="NODE2409",
        parallel_index="A"
    )


@pytest.fixture
def tfo8_static_network_data() -> Type8Transformer:
    return Type8Transformer(
        sending_node="NHVA1",
        receiving_node="NHVA2",
        parallel_index="1",
        rated_apparent_power=1000,
        cu_losses=0.21,
        iron_losses=0.02,
        noload_current=0.09,
        saturation_exponent=7,
        nominal_tap_number=0,
        initial_tap_position=0,
        regulating_mode=TransformerRegulatingMode.NOT_REGULATING,
        taps=[
            TransformerTap(
                tap_number=-10,
                sending_side_voltage=400,
                receiving_side_voltage=400,
                leakage_impedance=10,
                phase_shift_angle=-20
            ),
            TransformerTap(
                tap_number=0,
                sending_side_voltage=400,
                receiving_side_voltage=400,
                leakage_impedance=10,
                phase_shift_angle=0
            )
        ]
    )


@pytest.fixture
def dyn_gen_network_data() -> GeneratorDynamicPart:
    return GeneratorDynamicPart(
        name="GENA1",
        rated_apparent_power=1150,
        base_voltage_machine_side=24,
        inertia_constant=6.3,
        direct_transient_reactance=0.420
    )


@pytest.fixture
def ech_file_parser() -> EchEurostagFileParser:
    return EchEurostagFileParser(file_path=f"{TEST_DATA_FOLDER}/complete_case/complete_case.ech")


@pytest.fixture
def dta_file_parser() -> DtaEurostagFileParser:
    return DtaEurostagFileParser(file_path=f"{TEST_DATA_FOLDER}/complete_case/complete_case.dta")


@pytest.fixture
def file_parser() -> DtaEurostagFileParser:
    return DtaEurostagFileParser(file_path=f"{TEST_DATA_FOLDER}/complete_case/complete_case.dta")


@pytest.fixture
def file_parser_errors() -> DtaEurostagFileParser:
    return DtaEurostagFileParser(file_path=f"{TEST_DATA_FOLDER}/complete_case/complete_case_errors.dta")


@pytest.fixture
def topology_parser() -> EurostagTopologyParser:
    return EurostagTopologyParser(
        ech_file=f"{TEST_DATA_FOLDER}/complete_case/complete_case.ech",
        dta_file=f"{TEST_DATA_FOLDER}/complete_case/complete_case.dta"
    )


@pytest.fixture
def topology_parser_errors() -> EurostagTopologyParser:
    return EurostagTopologyParser(
        ech_file=f"{TEST_DATA_FOLDER}/complete_case/complete_case_errors.ech",
        dta_file=f"{TEST_DATA_FOLDER}/complete_case/complete_case.dta"
    )


@pytest.fixture
def topology_parser_bus_errors() -> EurostagTopologyParser:
    return EurostagTopologyParser(
        ech_file=f"{TEST_DATA_FOLDER}/complete_case/complete_case_errors_buses.ech",
        dta_file=f"{TEST_DATA_FOLDER}/complete_case/complete_case.dta"
    )


@pytest.fixture
def topology_parser_base_power_errors() -> EurostagTopologyParser:
    return EurostagTopologyParser(
        ech_file=f"{TEST_DATA_FOLDER}/complete_case/complete_case_errors_base_power.ech",
        dta_file=f"{TEST_DATA_FOLDER}/complete_case/complete_case.dta"
    )


@pytest.fixture
def complete_case_dta_content() -> Dict[DtaRecordType, Dict[str, List]]:
    return {
        DtaRecordType.FULL_EXTERNAL_PARAM_GENERATOR: [
            GeneratorDynamicPart(
                name="GEN A1",
                rated_apparent_power=1150,
                base_voltage_machine_side=24,
                inertia_constant=2.3,
                direct_transient_reactance=0.420
            ),
            GeneratorDynamicPart(
                name="GENB1",
                rated_apparent_power=444,
                base_voltage_machine_side=24,
                inertia_constant=6.3,
                direct_transient_reactance=0.420
            ),
            GeneratorDynamicPart(
                name="GENB2",
                rated_apparent_power=111,
                base_voltage_machine_side=24,
                inertia_constant=6.3,
                direct_transient_reactance=0.420
            ),
            GeneratorDynamicPart(
                name="NHVCEQ",
                rated_apparent_power=60000,
                base_voltage_machine_side=106.54,
                inertia_constant=6.3,
                direct_transient_reactance=0.420
            )
        ]
    }


@pytest.fixture
def complete_case_ech_content() -> Dict[EchRecordType, NetworkData]:
    return {
        EchRecordType.GENERAL_PARAMETERS: [
            NetworkParameters(base_power=0)
        ],
        EchRecordType.NODE: [
            Node(name="NGENA1", base_voltage=24),
            Node(name="NHVA1", base_voltage=380),
            Node(name="NGENB1", base_voltage=24),
            Node(name="NGENB2", base_voltage=24),
            Node(name="NHVA2", base_voltage=380),
            Node(name="NHVB1", base_voltage=380),
            Node(name="NHVD1", base_voltage=380),
            Node(name="NHVC1", base_voltage=380),
            Node(name="NHVC2", base_voltage=380),
            Node(name="NHV A3", base_voltage=380),
            Node(name="NHVA4", base_voltage=380),
            Node(name="NHVCEQ", base_voltage=100),
        ],
        EchRecordType.SLACK_BUS: [
            SlackBus(name="NHVCEQ", phase_angle=0)
        ],
        EchRecordType.COUPLING_DEVICE: [
            CouplingDevice(sending_node="NHV A3", receiving_node="NHVA4", parallel_index="1")
        ],
        EchRecordType.LINE: [
            Line(
                sending_node="NHVA1",
                receiving_node="NHV A3",
                parallel_index="1",
                resistance=0.00206,
                reactance=0.02285,
                semi_shunt_conductance=0,
                semi_shunt_susceptance=0.27869,
                rated_apparent_power=1000
            ),
            Line(
                sending_node="NHV A3",
                receiving_node="NHVD1",
                parallel_index="1",
                resistance=0.00103,
                reactance=0.01142,
                semi_shunt_conductance=0,
                semi_shunt_susceptance=0.13935,
                rated_apparent_power=1000
            ),
            Line(
                sending_node="NHVC1",
                receiving_node="NHVA2",
                parallel_index="1",
                resistance=0.00206,
                reactance=0.02285,
                semi_shunt_conductance=0,
                semi_shunt_susceptance=0.27869,
                rated_apparent_power=1000
            ),
            Line(
                sending_node="NHVC1",
                receiving_node="NHVC2",
                parallel_index="1",
                resistance=0.00103,
                reactance=0.01142,
                semi_shunt_conductance=0,
                semi_shunt_susceptance=0.13935,
                rated_apparent_power=1000
            ),
            Line(
                sending_node="NHVD1",
                receiving_node="NHVC1",
                parallel_index="1",
                resistance=0.00206,
                reactance=0.02285,
                semi_shunt_conductance=0,
                semi_shunt_susceptance=0.27869,
                rated_apparent_power=1000
            ),
            Line(
                sending_node="NHVC2",
                receiving_node="NHVB1",
                parallel_index="1",
                resistance=0.00206,
                reactance=0.02285,
                semi_shunt_conductance=0,
                semi_shunt_susceptance=0.27869,
                rated_apparent_power=500
            ),
            Line(
                sending_node="NHVC2",
                receiving_node="NHVB1",
                parallel_index="2",
                resistance=0.00206,
                reactance=0.02285,
                semi_shunt_conductance=0,
                semi_shunt_susceptance=0.27869,
                rated_apparent_power=500
            ),
            Line(
                sending_node="NHVD1",
                receiving_node="NHVB1",
                parallel_index="1",
                resistance=0.00103,
                reactance=0.01142,
                semi_shunt_conductance=0,
                semi_shunt_susceptance=0.13935,
                rated_apparent_power=500
            ),
            Line(
                sending_node="NHVD1",
                receiving_node="NHVB1",
                parallel_index="2",
                resistance=0.00103,
                reactance=0.01142,
                semi_shunt_conductance=0,
                semi_shunt_susceptance=0.13935,
                rated_apparent_power=500
            ),
            Line(
                sending_node="NHVC1",
                receiving_node="NHVCEQ",
                parallel_index="1",
                resistance=0.002,
                reactance=0.010,
                semi_shunt_conductance=0,
                semi_shunt_susceptance=0.27,
                rated_apparent_power=9999
            ),
            Line(
                sending_node="NHVC2",
                receiving_node="NHVCEQ",
                parallel_index="1",
                resistance=0.002,
                reactance=0.021,
                semi_shunt_conductance=0,
                semi_shunt_susceptance=0.27,
                rated_apparent_power=9999
            )
        ],
        EchRecordType.GENERATOR: [
            GeneratorStaticPart(
                name="GEN A1",
                state=State.CONNECTED,
                bus_name="NGENA1",
                min_active_power=-999999,
                active_power=900,
                max_active_power=999999,
                min_reactive_power=-9999,
                reactive_power=0,
                max_reactive_power=9999,
                target_voltage=24,
                regulating_mode=GeneratorRegulatingMode.REGULATING
            ),
            GeneratorStaticPart(
                name="GENB1",
                state=State.CONNECTED,
                bus_name="NGENB1",
                min_active_power=-999999,
                active_power=400,
                max_active_power=999999,
                min_reactive_power=-999999,
                reactive_power=190,
                max_reactive_power=999999,
                regulating_mode=GeneratorRegulatingMode.NOT_REGULATING
            ),
            GeneratorStaticPart(
                name="GENB2",
                state=State.CONNECTED,
                bus_name="NGENB2",
                min_active_power=-999999,
                active_power=100,
                max_active_power=999999,
                min_reactive_power=-999999,
                reactive_power=45,
                max_reactive_power=999999,
                regulating_mode=GeneratorRegulatingMode.NOT_REGULATING
            ),
            GeneratorStaticPart(
                name="NHVCEQ",
                state=State.CONNECTED,
                bus_name="NHVCEQ",
                min_active_power=-999999,
                active_power=2504,
                max_active_power=999999,
                min_reactive_power=-999999,
                reactive_power=835,
                max_reactive_power=999999,
                target_voltage=106.54,
                regulating_mode=GeneratorRegulatingMode.REGULATING
            ),
            GeneratorStaticPart(
                name="NHVC2",
                state=State.CONNECTED,
                bus_name="NHVC2",
                min_active_power=-999999,
                active_power=600,
                max_active_power=999999,
                min_reactive_power=-999999,
                reactive_power=200,
                max_reactive_power=999999,
                regulating_mode=GeneratorRegulatingMode.NOT_REGULATING
            )
        ],
        EchRecordType.TYPE1_TRANSFORMER: [
            Type1Transformer(
                sending_node="NGENA1",
                receiving_node="NHVA1",
                parallel_index="1",
                resistance=0.000185,
                reactance=0.00770,
                rated_apparent_power=1300,
                transformation_ratio=1.1
            ),
            Type1Transformer(
                sending_node="NGENB1",
                receiving_node="NHVB1",
                parallel_index="1",
                resistance=0.000541,
                reactance=0.02251,
                rated_apparent_power=444,
                transformation_ratio=1.1
            ),
            Type1Transformer(
                sending_node="NGENB2",
                receiving_node="NHVB1",
                parallel_index="1",
                resistance=0.02164,
                reactance=0.09006,
                rated_apparent_power=111,
                transformation_ratio=1.1
            )
        ],
        EchRecordType.TYPE8_TRANSFORMER: [
            Type8Transformer(
                sending_node="NHVA1",
                receiving_node="NHVA2",
                parallel_index="1",
                rated_apparent_power=1000,
                cu_losses=0.21,
                iron_losses=0.02,
                noload_current=0.09,
                saturation_exponent=7,
                nominal_tap_number=0,
                initial_tap_position=0,
                regulating_mode=TransformerRegulatingMode.NOT_REGULATING,
                taps=[
                    TransformerTap(
                        tap_number=-10,
                        sending_side_voltage=400,
                        receiving_side_voltage=400,
                        leakage_impedance=10,
                        phase_shift_angle=-20
                    ),
                    TransformerTap(
                        tap_number=0,
                        sending_side_voltage=400,
                        receiving_side_voltage=400,
                        leakage_impedance=10,
                        phase_shift_angle=0
                    ),
                    TransformerTap(
                        tap_number=10,
                        sending_side_voltage=400,
                        receiving_side_voltage=400,
                        leakage_impedance=10,
                        phase_shift_angle=20
                    )
                ]
            ),
            Type8Transformer(
                sending_node="NHVA1",
                receiving_node="NHV A3",
                parallel_index="2",
                rated_apparent_power=1000,
                cu_losses=0.22,
                iron_losses=0.03,
                noload_current=0.09,
                saturation_exponent=7,
                nominal_tap_number=0,
                initial_tap_position=0,
                regulating_mode=TransformerRegulatingMode.NOT_REGULATING,
                taps=[
                    TransformerTap(
                        tap_number=-10,
                        sending_side_voltage=400,
                        receiving_side_voltage=400,
                        leakage_impedance=10,
                        phase_shift_angle=-20
                    ),
                    TransformerTap(
                        tap_number=0,
                        sending_side_voltage=400,
                        receiving_side_voltage=400,
                        leakage_impedance=10,
                        phase_shift_angle=0
                    ),
                    TransformerTap(
                        tap_number=10,
                        sending_side_voltage=400,
                        receiving_side_voltage=400,
                        leakage_impedance=10,
                        phase_shift_angle=20
                    )
                ]
            )
        ],
        EchRecordType.LOAD: [
            Load(
                name="LOAD",
                state=State.CONNECTED,
                bus_name="NHVA1",
                active_power=100,
                reactive_power=10
            ),
            Load(
                name="NHVA1",
                state=State.CONNECTED,
                bus_name="NHVA1",
                active_power=900,
                reactive_power=90
            ),
            Load(
                name="NHVB1",
                state=State.CONNECTED,
                bus_name="NHVB1",
                active_power=1000,
                reactive_power=300
            ),
            Load(
                name="NHVC1",
                state=State.CONNECTED,
                bus_name="NHVC1",
                active_power=500,
                reactive_power=100
            ),
            Load(
                name="NHVCEQ",
                state=State.CONNECTED,
                bus_name="NHVCEQ",
                active_power=700,
                reactive_power=150
            )
        ],
        EchRecordType.CAPACITOR_BANK: [
            CapacitorBank(
                name="CBANK1",
                bus_name="NHVD1",
                number_active_steps=1,
                active_loss_on_step=0,
                reactive_power_on_step=150
            ),
            CapacitorBank(
                name="CBANK2",
                bus_name="NHVD1",
                number_active_steps=2,
                active_loss_on_step=1,
                reactive_power_on_step=-50
            )
        ],
        EchRecordType.SVC: [
            StaticVarCompensator(
                name="SVC 01",
                state=State.NOT_CONNECTED,
                bus_name="NHVC1"
            ),
            StaticVarCompensator(
                name="SVC 02",
                state=State.CONNECTED,
                bus_name="NHVB1"
            )
        ],
        EchRecordType.HVDC_VSC_CONVERTER: [
            HVDCVoltageSourceConverter(
                name="CONV_01",
                bus_name="NHVC1"
            ),
            HVDCVoltageSourceConverter(
                name="CONV_02",
                bus_name="NHVA1"
            ),
            HVDCVoltageSourceConverter(
                name="CONV_04",
                state=HVDCConverterState.OFF,
                bus_name="NHVA2"
            )
        ],
        EchRecordType.HVDC_CSC_CONVERTER: [
            HVDCCurrentSourceConverter(
                name="CONV_03",
                bus_name="NHVA2"
            )
        ]
    }


@pytest.fixture
def complete_case_topology() -> topology_dtos.NetworkTopology:
    slack_bus = topology_dtos.SlackBus(
        name="NHVCEQ",
        base_voltage=Value(value=100, unit=Unit.KV),
        phase_angle=Value(value=0, unit=Unit.DEG)
    )
    buses = [
        topology_dtos.Bus(name="NGENA1", base_voltage=Value(value=24, unit=Unit.KV)),
        topology_dtos.Bus(name="NHVA1", base_voltage=Value(value=380, unit=Unit.KV)),
        topology_dtos.Bus(name="NGENB1", base_voltage=Value(value=24, unit=Unit.KV)),
        topology_dtos.Bus(name="NGENB2", base_voltage=Value(value=24, unit=Unit.KV)),
        topology_dtos.Bus(name="NHVA2", base_voltage=Value(value=380, unit=Unit.KV)),
        topology_dtos.Bus(name="NHVB1", base_voltage=Value(value=380, unit=Unit.KV)),
        topology_dtos.Bus(name="NHVD1", base_voltage=Value(value=380, unit=Unit.KV)),
        topology_dtos.Bus(name="NHVC1", base_voltage=Value(value=380, unit=Unit.KV)),
        topology_dtos.Bus(name="NHVC2", base_voltage=Value(value=380, unit=Unit.KV)),
        topology_dtos.Bus(name="NHV A3", base_voltage=Value(value=380, unit=Unit.KV)),
        topology_dtos.Bus(name="NHVA4", base_voltage=Value(value=380, unit=Unit.KV)),
        slack_bus
    ]
    branches = [
        topology_dtos.Branch(
            sending_bus=buses[1],
            receiving_bus=buses[9],
            parallel_elements={
                "1": topology_dtos.Line(
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    resistance=Value(value=0.00206*380**2/100, unit=Unit.OHM),
                    reactance=Value(value=0.02285*380**2/100, unit=Unit.OHM),
                    shunt_conductance=Value(value=0, unit=Unit.S),
                    shunt_susceptance=Value(value=2*0.27869/(380**2/100), unit=Unit.S)
                ),
                "2": topology_dtos.Transformer8(
                    sending_node=buses[1].name,
                    receiving_node=buses[9].name,
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    initial_tap_number=0,
                    base_impedance=Value(value=400**2/1000, unit=Unit.OHM),
                    primary_base_voltage=Value(value=400, unit=Unit.KV),
                    secondary_base_voltage=Value(value=400, unit=Unit.KV),
                    phase_shift_angle=Value(value=0, unit=Unit.DEG)
                )
            }
        ),
        topology_dtos.Branch(
            sending_bus=buses[9],
            receiving_bus=buses[6],
            parallel_elements={
                "1": topology_dtos.Line(
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    resistance=Value(value=0.00103*380**2/100, unit=Unit.OHM),
                    reactance=Value(value=0.01142*380**2/100, unit=Unit.OHM),
                    shunt_conductance=Value(value=0, unit=Unit.S),
                    shunt_susceptance=Value(value=2*0.13935/(380**2/100), unit=Unit.S)
                )
            }
        ),
        topology_dtos.Branch(
            sending_bus=buses[7],
            receiving_bus=buses[4],
            parallel_elements={
                "1": topology_dtos.Line(
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    resistance=Value(value=0.00206*380**2/100, unit=Unit.OHM),
                    reactance=Value(value=0.02285*380**2/100, unit=Unit.OHM),
                    shunt_conductance=Value(value=0, unit=Unit.S),
                    shunt_susceptance=Value(value=2*0.27869/(380**2/100), unit=Unit.S)
                )
            }
        ),
        topology_dtos.Branch(
            sending_bus=buses[7],
            receiving_bus=buses[8],
            parallel_elements={
                "1": topology_dtos.Line(
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    resistance=Value(value=0.00103*380**2/100, unit=Unit.OHM),
                    reactance=Value(value=0.01142*380**2/100, unit=Unit.OHM),
                    shunt_conductance=Value(value=0, unit=Unit.S),
                    shunt_susceptance=Value(value=2*0.13935/(380**2/100), unit=Unit.S)
                )
            }
        ),
        topology_dtos.Branch(
            sending_bus=buses[6],
            receiving_bus=buses[7],
            parallel_elements={
                "1": topology_dtos.Line(
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    resistance=Value(value=0.00206*380**2/100, unit=Unit.OHM),
                    reactance=Value(value=0.02285*380**2/100, unit=Unit.OHM),
                    shunt_conductance=Value(value=0, unit=Unit.S),
                    shunt_susceptance=Value(value=2*0.27869/(380**2/100), unit=Unit.S)
                )
            }
        ),
        topology_dtos.Branch(
            sending_bus=buses[8],
            receiving_bus=buses[5],
            parallel_elements={
                "1": topology_dtos.Line(
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    resistance=Value(value=0.00206*380**2/100, unit=Unit.OHM),
                    reactance=Value(value=0.02285*380**2/100, unit=Unit.OHM),
                    shunt_conductance=Value(value=0, unit=Unit.S),
                    shunt_susceptance=Value(value=2*0.27869/(380**2/100), unit=Unit.S)
                ),
                "2": topology_dtos.Line(
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    resistance=Value(value=0.00206*380**2/100, unit=Unit.OHM),
                    reactance=Value(value=0.02285*380**2/100, unit=Unit.OHM),
                    shunt_conductance=Value(value=0, unit=Unit.S),
                    shunt_susceptance=Value(value=2*0.27869/(380**2/100), unit=Unit.S)
                )
            }
        ),
        topology_dtos.Branch(
            sending_bus=buses[6],
            receiving_bus=buses[5],
            parallel_elements={
                "1": topology_dtos.Line(
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    resistance=Value(value=0.00103*380**2/100, unit=Unit.OHM),
                    reactance=Value(value=0.01142*380**2/100, unit=Unit.OHM),
                    shunt_conductance=Value(value=0, unit=Unit.S),
                    shunt_susceptance=Value(value=2*0.13935/(380**2/100), unit=Unit.S)
                ),
                "2": topology_dtos.Line(
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    resistance=Value(value=0.00103*380**2/100, unit=Unit.OHM),
                    reactance=Value(value=0.01142*380**2/100, unit=Unit.OHM),
                    shunt_conductance=Value(value=0, unit=Unit.S),
                    shunt_susceptance=Value(value=2*0.13935/(380**2/100), unit=Unit.S)
                )
            }
        ),
        topology_dtos.Branch(
            sending_bus=buses[7],
            receiving_bus=slack_bus,
            parallel_elements={
                "1": topology_dtos.Line(
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    resistance=Value(value=0.002*380, unit=Unit.OHM),
                    reactance=Value(value=0.01*380, unit=Unit.OHM),
                    shunt_conductance=Value(value=0, unit=Unit.S),
                    shunt_susceptance=Value(value=2*0.27/380, unit=Unit.S)
                )
            }
        ),
        topology_dtos.Branch(
            sending_bus=buses[8],
            receiving_bus=slack_bus,
            parallel_elements={
                "1": topology_dtos.Line(
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    resistance=Value(value=0.002*380, unit=Unit.OHM),
                    reactance=Value(value=0.021*380, unit=Unit.OHM),
                    shunt_conductance=Value(value=0, unit=Unit.S),
                    shunt_susceptance=Value(value=2*0.27/380, unit=Unit.S)
                )
            }
        ),
        topology_dtos.Branch(
            sending_bus=buses[0],
            receiving_bus=buses[1],
            parallel_elements={
                "1": topology_dtos.Transformer1(
                    sending_node=buses[0].name,
                    receiving_node=buses[1].name,
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    base_impedance=Value(value=1444, unit=Unit.OHM),
                    ratio=1.1
                )
            }
        ),
        topology_dtos.Branch(
            sending_bus=buses[2],
            receiving_bus=buses[5],
            parallel_elements={
                "1": topology_dtos.Transformer1(
                    sending_node=buses[2].name,
                    receiving_node=buses[5].name,
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    ratio=1.1,
                    base_impedance=Value(value=1444, unit=Unit.OHM),
                )
            }
        ),
        topology_dtos.Branch(
            sending_bus=buses[3],
            receiving_bus=buses[5],
            parallel_elements={
                "1": topology_dtos.Transformer1(
                    sending_node=buses[3].name,
                    receiving_node=buses[5].name,
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    ratio=1.1,
                    base_impedance=Value(value=1444, unit=Unit.OHM),
                )
            }
        ),
        topology_dtos.Branch(
            sending_bus=buses[1],
            receiving_bus=buses[4],
            parallel_elements={
                "1": topology_dtos.Transformer8(
                    sending_node=buses[1].name,
                    receiving_node=buses[4].name,
                    closed_at_sending_bus=True,
                    closed_at_receiving_bus=True,
                    initial_tap_number=0,
                    base_impedance=Value(value=160, unit=Unit.OHM),
                    primary_base_voltage=Value(value=400, unit=Unit.KV),
                    secondary_base_voltage=Value(value=400, unit=Unit.KV),
                    phase_shift_angle=Value(value=0, unit=Unit.DEG)
                    # resistance=Value(value=0.0021*400**2/1000, unit=Unit.OHM)
                )
            }
        ),
        topology_dtos.Branch(
            sending_bus=buses[9],
            receiving_bus=buses[10],
            parallel_elements={
                "1": topology_dtos.Breaker(
                    closed=True
                )
            }
        )
    ]

    """
    closed_at_sending_bus=True,
    closed_at_receiving_bus=True,
    taps={
        -10: topology_dtos.TransformerTap(
            phase_shift_angle=Value(value=-20, unit=Unit.DEG),
            impedance=Value(value=0.1*400**2/1000, unit=Unit.OHM)
        ),
        0: topology_dtos.TransformerTap(
            phase_shift_angle=Value(value=0, unit=Unit.DEG),
            impedance=Value(value=0.1*400**2/1000, unit=Unit.OHM)
        ),
        10: topology_dtos.TransformerTap(
            phase_shift_angle=Value(value=20, unit=Unit.DEG),
            impedance=Value(value=0.1*400**2/1000, unit=Unit.OHM)
        )
    },
    """

    loads = [
        topology_dtos.Load(
            name="LOAD",
            bus=buses[1],
            connected=True,
            active_power=Value(value=100, unit=Unit.MW),
            reactive_power=Value(value=10, unit=Unit.MVAR)
        ),
        topology_dtos.Load(
            name="NHVA1",
            bus=buses[1],
            connected=True,
            active_power=Value(value=900, unit=Unit.MW),
            reactive_power=Value(value=90, unit=Unit.MVAR)
        ),
        topology_dtos.Load(
            name="NHVB1",
            bus=buses[5],
            connected=True,
            active_power=Value(value=1000, unit=Unit.MW),
            reactive_power=Value(value=300, unit=Unit.MVAR)
        ),
        topology_dtos.Load(
            name="NHVC1",
            bus=buses[7],
            connected=True,
            active_power=Value(value=500, unit=Unit.MW),
            reactive_power=Value(value=100, unit=Unit.MVAR)
        ),
        topology_dtos.Load(
            name="NHVCEQ",
            bus=slack_bus,
            connected=True,
            active_power=Value(value=700, unit=Unit.MW),
            reactive_power=Value(value=150, unit=Unit.MVAR)
        ),
        topology_dtos.Load(
            name="GEN_NHVC2",
            bus=buses[8],
            connected=True,
            active_power=Value(value=-600, unit=Unit.MW),
            reactive_power=Value(value=-200, unit=Unit.MVAR)
        )
    ]
    generators = [
        topology_dtos.Generator(
            name="GEN A1",
            connected=True,
            bus=buses[0],
            min_active_power=Value(value=-999999, unit=Unit.MW),
            active_power=Value(value=900, unit=Unit.MW),
            max_active_power=Value(value=999999, unit=Unit.MW),
            min_reactive_power=Value(value=-9999, unit=Unit.MVAR),
            reactive_power=Value(value=0, unit=Unit.MVAR),
            max_reactive_power=Value(value=9999, unit=Unit.MVAR),
            target_voltage=Value(value=24, unit=Unit.KV),
            direct_transient_reactance=Value(value=0.420*24**2/1150, unit=Unit.OHM),
            inertia_constant=Value(value=2645, unit=Unit.MWS_PER_MVA),
            regulating=True
        ),
        topology_dtos.Generator(
            name="GENB1",
            connected=True,
            bus=buses[2],
            min_active_power=Value(value=-999999, unit=Unit.MW),
            active_power=Value(value=400, unit=Unit.MW),
            max_active_power=Value(value=999999, unit=Unit.MW),
            min_reactive_power=Value(value=-999999, unit=Unit.MVAR),
            reactive_power=Value(value=190, unit=Unit.MVAR),
            max_reactive_power=Value(value=999999, unit=Unit.MVAR),
            direct_transient_reactance=Value(value=0.420*24**2/444, unit=Unit.OHM),
            inertia_constant=Value(value=2797.2, unit=Unit.MWS_PER_MVA),
            regulating=False
        ),
        topology_dtos.Generator(
            name="GENB2",
            connected=True,
            bus=buses[3],
            min_active_power=Value(value=-999999, unit=Unit.MW),
            active_power=Value(value=100, unit=Unit.MW),
            max_active_power=Value(value=999999, unit=Unit.MW),
            min_reactive_power=Value(value=-999999, unit=Unit.MVAR),
            reactive_power=Value(value=45, unit=Unit.MVAR),
            max_reactive_power=Value(value=999999, unit=Unit.MVAR),
            direct_transient_reactance=Value(value=0.420*24**2/111, unit=Unit.OHM),
            inertia_constant=Value(value=699.3, unit=Unit.MWS_PER_MVA),
            regulating=False
        ),
        topology_dtos.Generator(
            name="NHVCEQ",
            connected=True,
            bus=slack_bus,
            min_active_power=Value(value=-999999, unit=Unit.MW),
            active_power=Value(value=2504, unit=Unit.MW),
            max_active_power=Value(value=999999, unit=Unit.MW),
            min_reactive_power=Value(value=-999999, unit=Unit.MVAR),
            reactive_power=Value(value=835, unit=Unit.MVAR),
            max_reactive_power=Value(value=999999, unit=Unit.MVAR),
            target_voltage=Value(value=106.54, unit=Unit.KV),
            direct_transient_reactance=Value(value=0.420*106.54**2/60000, unit=Unit.OHM),
            inertia_constant=Value(value=378000, unit=Unit.MWS_PER_MVA),
            regulating=True
        )
    ]
    capacitor_banks = [
        topology_dtos.CapacitorBank(
            name="CBANK1",
            bus=buses[6],
            active_power=Value(value=0, unit=Unit.MW),
            reactive_power=Value(value=150, unit=Unit.MVAR)
        ),
        topology_dtos.CapacitorBank(
            name="CBANK2",
            bus=buses[6],
            connected=True,
            active_power=Value(value=2 / 1000, unit=Unit.MW),
            reactive_power=Value(value=-50 * 2, unit=Unit.MVAR)
        )
    ]
    static_var_compensators = [
        topology_dtos.StaticVarCompensator(
            name="SVC 01",
            connected=False,
            bus=buses[7]
        ),
        topology_dtos.StaticVarCompensator(
            name="SVC 02",
            connected=True,
            bus=buses[5]
        )
    ]
    hvdc_converters = [
        topology_dtos.HVDCConverter(
            name="CONV_03",
            connected=True,
            bus=buses[4]
        ),
        topology_dtos.HVDCConverter(
            name="CONV_01",
            connected=True,
            bus=buses[7]
        ),
        topology_dtos.HVDCConverter(
            name="CONV_02",
            connected=True,
            bus=buses[1]
        ),
        topology_dtos.HVDCConverter(
            name="CONV_04",
            connected=False,
            bus=buses[4]
        )
    ]
    return topology_dtos.NetworkTopology(
        base_power=Value(value=100, unit=Unit.MVA),
        buses=buses,
        slack_buses=[slack_bus],
        branches=branches,
        loads=loads,
        generators=generators,
        capacitor_banks=capacitor_banks,
        static_var_compensators=static_var_compensators,
        hvdc_converters=hvdc_converters
    )
