# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest

from tests import TEST_DATA_FOLDER
from deeac.adapters.load_flow.eurostag.table_description import TableType, TableDescription
from deeac.adapters.load_flow.eurostag.load_flow_parser import FILE_DESCRIPTION, EurostagLoadFlowParser
from deeac.adapters.load_flow.eurostag.dtos import Transformer, TransformerType, Result, HVDCConverter
import deeac.domain.ports.dtos.load_flow as load_flow_dtos
from deeac.domain.ports.dtos import Value, Unit


@pytest.fixture
def tfo_table_description() -> TableDescription:
    return FILE_DESCRIPTION[TableType.TRANSFORMERS]


@pytest.fixture
def results_table_description() -> TableDescription:
    return FILE_DESCRIPTION[TableType.RESULTS]


@pytest.fixture
def hvdc_converter_table_description() -> TableDescription:
    return FILE_DESCRIPTION[TableType.HVDC_CONVERTERS_RESULTS]


@pytest.fixture
def load_flow_parser() -> EurostagLoadFlowParser:
    return EurostagLoadFlowParser(load_flow_results_file=f"{TEST_DATA_FOLDER}/complete_case/complete_case.lf")


@pytest.fixture
def load_flow_parser_errors() -> EurostagLoadFlowParser:
    return EurostagLoadFlowParser(load_flow_results_file=f"{TEST_DATA_FOLDER}/complete_case/complete_case_errors.lf")


@pytest.fixture
def load_flow_parser_divergence() -> EurostagLoadFlowParser:
    return EurostagLoadFlowParser(load_flow_results_file=f"{TEST_DATA_FOLDER}/complete_case/complete_case_errors_divergence.lf")


@pytest.fixture
def tfo1() -> Transformer:
    return Transformer(
        sending_node="NGENB1",
        receiving_node="NHVA1",
        parallel_index="2",
        type=TransformerType.FIXED_REAL_RATIO
    )


@pytest.fixture
def tfo8() -> Transformer:
    return Transformer(
        sending_node="NGEN A1",
        receiving_node="NHVB1",
        parallel_index="1",
        type=TransformerType.DETAILED
    )


@pytest.fixture
def tfo5() -> Transformer:
    return Transformer(
        sending_node="NGENA2",
        receiving_node="NH VA 2",
        parallel_index="1",
        type=TransformerType.FORTESCUE_GENERAL
    )


@pytest.fixture
def bus_result() -> Result:
    return Result(
        area="A",
        node_name="NGEN A1",
        voltage=24,
        phase_angle=-15.17,
        production_active_power=900,
        production_reactive_power=322.12,
        load_active_power=0,
        load_reactive_power=0
    )


@pytest.fixture
def bus_result2() -> Result:
    return Result(
        area="A",
        node_name="NHVB1",
        voltage=10,
        phase_angle=-13.30,
        production_active_power=100,
        production_reactive_power=343.12,
        load_active_power=0,
        load_reactive_power=0
    )


@pytest.fixture
def disconnected_bus_result() -> Result:
    return Result(
        area="A",
        node_name="NHVA3",
        voltage=0,
        phase_angle=0
    )


@pytest.fixture
def tfo_result() -> Result:
    return Result(
        connected_node_name="NHVB1",
        branch_parallel_index="1",
        transformer_tap=9
    )


@pytest.fixture
def tfo_result2() -> Result:
    return Result(
        connected_node_name="NHVA3",
        branch_parallel_index="2",
        transformer_tap=0
    )


@pytest.fixture
def tfo_result3() -> Result:
    return Result(
        connected_node_name="NHVB1",
        branch_parallel_index="2",
        transformer_tap=0
    )


@pytest.fixture
def tfo_result_error() -> Result:
    return Result(
        connected_node_name="NHVB1",
        branch_parallel_index="1",
        transformer_tap=None
    )


@pytest.fixture
def generator_result() -> Result:
    return Result(
        area="GE",
        node_name="GENA1",
        production_active_power=800,
        production_reactive_power=453.12
    )


@pytest.fixture
def hvdc_converter_result() -> HVDCConverter:
    return HVDCConverter(
        converter_name="CONV 1",
        active_power=900,
        reactive_power=322.12
    )


@pytest.fixture
def svc_result() -> Result:
    return Result(
        area="SV",
        node_name="SVC_1",
        production_reactive_power=0.05
    )



@pytest.fixture
def complete_case_lf_results() -> load_flow_dtos.LoadFlowResults:
    return load_flow_dtos.LoadFlowResults(
        loads={
            "LOAD": load_flow_dtos.Load(
                name="LOAD",
                active_power=Value(value=100.0, unit=Unit.MW),
                reactive_power = Value(value=10.0, unit= Unit.MVAR)
            ),
            "NHVA1": load_flow_dtos.Load(
                name="NHVA1",
                active_power=Value(value=900.0, unit=Unit.MW),
                reactive_power = Value(value=90.0, unit= Unit.MVAR)
            ),
            "NHVC1": load_flow_dtos.Load(
                name="NHVC1",
                active_power=Value(value=500.0, unit=Unit.MW),
                reactive_power = Value(value=100.0, unit= Unit.MVAR)
            ),
            "NHVC2": load_flow_dtos.Load(
                name="NHVC2",
                active_power=Value(value=600.0, unit=Unit.MW),
                reactive_power = Value(value=200.0, unit= Unit.MVAR)
            ),
            "NHVCEQ": load_flow_dtos.Load(
                name="NHVCEQ",
                active_power=Value(value=700.0, unit=Unit.MW),
                reactive_power = Value(value=150.0, unit= Unit.MVAR)
            )
        },
        buses={
            "NGENA1": load_flow_dtos.Bus(
                name="NGENA1",
                voltage=Value(value=24, unit=Unit.KV),
                phase_angle=Value(value=-105.17, unit=Unit.DEG)
            ),
            "NHVA1": load_flow_dtos.Bus(
                name="NHVA1",
                voltage=Value(value=409.55, unit=Unit.KV),
                phase_angle=Value(value=-18.49, unit=Unit.DEG)
            ),
            "NHVA2": load_flow_dtos.Bus(
                name="NHVA2",
                voltage=Value(value=406.94, unit=Unit.KV),
                phase_angle=Value(value=-2.21, unit=Unit.DEG)
            ),
            "NHV A3": load_flow_dtos.Bus(
                name="NHV A3",
                voltage=Value(value=403.58, unit=Unit.KV),
                phase_angle=Value(value=-13.59, unit=Unit.DEG)
            ),
            "NGENB1": load_flow_dtos.Bus(
                name="NGENB1",
                voltage=Value(value=23.65, unit=Unit.KV),
                phase_angle=Value(value=-6.56, unit=Unit.DEG)
            ),
            "NGENB2": load_flow_dtos.Bus(
                name="NGENB2",
                voltage=Value(value=23.99, unit=Unit.KV),
                phase_angle=Value(value=-7.06, unit=Unit.DEG)
            ),
            "NHVB1": load_flow_dtos.Bus(
                name="NHVB1",
                voltage=Value(value=397.33, unit=Unit.KV),
                phase_angle=Value(value=-11.07, unit=Unit.DEG)
            ),
            "NHVC1": load_flow_dtos.Bus(
                name="NHVC1",
                voltage=Value(value=398.33, unit=Unit.KV),
                phase_angle=Value(value=-5.79, unit=Unit.DEG)
            ),
            "NHVC2": load_flow_dtos.Bus(
                name="NHVC2",
                voltage=Value(value=395.63, unit=Unit.KV),
                phase_angle=Value(value=-8.07, unit=Unit.DEG)
            ),
            "NHVCEQ": load_flow_dtos.Bus(
                name="NHVCEQ",
                voltage=Value(value=106.54, unit=Unit.KV),
                phase_angle=Value(value=0, unit=Unit.DEG)
            ),
            "NHVD1": load_flow_dtos.Bus(
                name="NHVD1",
                voltage=Value(value=399.81, unit=Unit.KV),
                phase_angle=Value(value=-11.06, unit=Unit.DEG)
            )
        },
        generators={
            "GEN A1": load_flow_dtos.Generator(
                name="GEN A1",
                active_power=Value(value=900, unit=Unit.MW),
                reactive_power=Value(value=322.12, unit=Unit.MVAR)
            ),
            "GENB1": load_flow_dtos.Generator(
                name="GENB1",
                active_power=Value(value=400, unit=Unit.MW),
                reactive_power=Value(value=190, unit=Unit.MVAR)
            ),
            "GENB2": load_flow_dtos.Generator(
                name="GENB2",
                active_power=Value(value=100, unit=Unit.MW),
                reactive_power=Value(value=45, unit=Unit.MVAR)
            ),
            "NHVCEQ": load_flow_dtos.Generator(
                name="NHVCEQ",
                active_power=Value(value=2447.5, unit=Unit.MW),
                reactive_power=Value(value=221.88, unit=Unit.MVAR)
            )
        },
        transformers={
            ("NHVA1", "NHVA2", "1"): load_flow_dtos.Transformer(
                sending_bus="NHVA1",
                receiving_bus="NHVA2",
                parallel_id="1",
                tap_number=9
            )
        },
        static_var_compensators={
            "SVC 01": load_flow_dtos.StaticVarCompensator(
                name="SVC 01",
                reactive_power=Value(value=0.15, unit=Unit.MVAR)
            ),
            "SVC 02": load_flow_dtos.StaticVarCompensator(
                name="SVC 02",
                reactive_power=Value(value=0.20, unit=Unit.MVAR)
            )
        },
        hvdc_converters={
            "CONV_01": load_flow_dtos.HVDCConverter(
                name="CONV_01",
                active_power=Value(value=997.57, unit=Unit.MW),
                reactive_power=Value(value=-190.94, unit=Unit.MVAR)
            ),
            "CONV_02": load_flow_dtos.HVDCConverter(
                name="CONV_02",
                active_power=Value(value=290.4, unit=Unit.MW),
                reactive_power=Value(value=-310.51, unit=Unit.MVAR)
            ),
            "CONV_03": load_flow_dtos.HVDCConverter(
                name="CONV_03",
                active_power=Value(value=400.57, unit=Unit.MW),
                reactive_power=Value(value=600.0, unit=Unit.MVAR)
            ),
            "CONV_04": load_flow_dtos.HVDCConverter(
                name="CONV_04",
                active_power=Value(value=90.7, unit=Unit.MW),
                reactive_power=Value(value=-90.40, unit=Unit.MVAR)
            )
        },
        transformer_nodes_data={
            "NGENA1": load_flow_dtos.TransformerNodeData(
                orig_node="NGENA1", zone="A", types=["1"], parallel_ids = ["1"], nodes = [0],
                resistances = [".00018"], reactances = [".007690"],
                shunt_susceptances = [".000000"], shunt_conductances = [".000"]
            ),
            "NHVA1": load_flow_dtos.TransformerNodeData(
                orig_node="NHVA1", zone="A", types=["1", "8"], parallel_ids = ["1", "1"],
                nodes = [0, 2], resistances = [".00018", ".00023"],
                reactances = [".007690", ".011078"], shunt_susceptances = [".000000", ".005821"],
                shunt_conductances = [".000", ".002"]
            ),
            "NHVA2": load_flow_dtos.TransformerNodeData(
                orig_node="NHVA2", zone="A", types=["8"], parallel_ids = ["1"], nodes = [0],
                resistances = [".00023"], reactances = [".011078"],
                shunt_susceptances = [".005821"], shunt_conductances = [".002"]
            ),
            "NHV A3": load_flow_dtos.TransformerNodeData(
                orig_node="NHV A3", zone="A", types=[], parallel_ids=[], nodes=[], resistances=[], reactances=[],
                shunt_susceptances=[], shunt_conductances=[]
            ),
            "NGENB1": load_flow_dtos.TransformerNodeData(
                orig_node="NGENB1", zone="B", types=["1"], parallel_ids = ["1"], nodes = [6],
                resistances = [".00054"], reactances = [".022510"],
                shunt_susceptances = [".000000"], shunt_conductances = [".000"]
            ),
            "NGENB2": load_flow_dtos.TransformerNodeData(
                orig_node="NGENB2", zone="B", types=["1"], parallel_ids = ["1"], nodes = [6],
                resistances = [".02164"], reactances = [".090060"],
                shunt_susceptances = [".000000"], shunt_conductances = [".000"]
            ),
            "NHVB1": load_flow_dtos.TransformerNodeData(
                orig_node="NHVB1", zone="B", types=["1", "1"], parallel_ids = ["1", "1"],
                nodes = [4, 5], resistances = [".00054", ".02164"],
                reactances = [".022510", ".090060"], shunt_susceptances = [".000000", ".000000"],
                shunt_conductances = [".000", ".000"]
            ),
            "NHVC1": load_flow_dtos.TransformerNodeData(
                orig_node="NHVC1", zone="C", types=[], parallel_ids=[], nodes=[], resistances=[], reactances=[],
                shunt_susceptances=[], shunt_conductances=[]
            ),
            "NHVC2": load_flow_dtos.TransformerNodeData(
                orig_node="NHVC2", zone="C", types=[], parallel_ids=[], nodes=[], resistances=[], reactances=[],
                shunt_susceptances=[], shunt_conductances=[]
            ),
            "NHVCEQ": load_flow_dtos.TransformerNodeData(
                orig_node="NHVCEQ", zone="C", types=[], parallel_ids=[], nodes=[], resistances=[], reactances=[],
                shunt_susceptances=[], shunt_conductances=[]
            ),
            "NHVD1": load_flow_dtos.TransformerNodeData(
                orig_node="NHVD1", zone="D", types=[], parallel_ids=[], nodes=[], resistances=[], reactances=[],
                shunt_susceptances=[], shunt_conductances=[]
            )
        },
        transformer_tap_data={
            "NHVA2_NHVA1_1": load_flow_dtos.TransformerTapData(
                sending_node="NHVA1", receiving_node="NHVA2", tap_numbers=[-10, 0, 10],
                phase_angles=[-20.0, 0.0, 20.0],
                sending_node_voltages=[400.0, 400.0, 400.0],
                receiving_node_voltages=[400.0, 400.0, 400.0]
            )
        }
    )
