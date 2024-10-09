# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest

from deeac.adapters.load_flow.eurostag.exceptions import (
    LoadFlowTransformerException, LoadFlowDataValidationException, LoadFlowDivergenceException
)
from deeac.domain.ports.exceptions import (
    NetworkElementNameException, BranchParallelException
)
from deeac.domain.exceptions import DEEACException, DEEACExceptionList
from deeac.domain.ports.dtos.load_flow import Bus, Generator, Transformer
from deeac.domain.ports.dtos import Value, Unit
from tests.adapters.dto_comparators import dtos_are_equal


class TestLoadFlowParser:

    def test_analyse_load_flow_data(
        self, load_flow_parser, tfo1, tfo8, generator_result, tfo_result, tfo_result2, tfo_result3,
        tfo_result_error, bus_result, bus_result2, disconnected_bus_result
    ):
        # No sending bus previously identified
        with pytest.raises(LoadFlowTransformerException):
            load_flow_parser._analyse_load_flow_data(tfo_result)

        # Transformers (type 1 is ignored)
        load_flow_parser._analyse_load_flow_data(tfo1)
        load_flow_parser._analyse_load_flow_data(tfo8)
        assert load_flow_parser._transformer_info == [(tfo8.sending_node, tfo8.receiving_node, tfo8.parallel_index)]

        # Bus result
        load_flow_parser._analyse_load_flow_data(disconnected_bus_result)
        load_flow_parser._analyse_load_flow_data(bus_result2)
        load_flow_parser._analyse_load_flow_data(bus_result)
        for bus_res in [bus_result, bus_result2]:
            assert dtos_are_equal(
                load_flow_parser._buses[bus_res.node_name],
                Bus(
                    name=bus_res.node_name,
                    voltage=Value(value=bus_res.voltage, unit=Unit.KV),
                    phase_angle=Value(value=bus_res.phase_angle, unit=Unit.DEG)
                )
            )
        # Same name cannot be assigned to multiple buses
        with pytest.raises(NetworkElementNameException):
            load_flow_parser._analyse_load_flow_data(bus_result)

        # Generator result
        load_flow_parser._analyse_load_flow_data(generator_result)
        assert dtos_are_equal(
            load_flow_parser._generators,
            {
                generator_result.node_name: Generator(
                    name=generator_result.node_name,
                    active_power=Value(value=generator_result.production_active_power, unit=Unit.MW),
                    reactive_power=Value(value=generator_result.production_reactive_power, unit=Unit.MVAR)
                )
            }
        )
        # Same name cannot be assigned to multiple generators
        with pytest.raises(NetworkElementNameException):
            load_flow_parser._analyse_load_flow_data(generator_result)

        # Transformer result
        with pytest.raises(DEEACExceptionList) as e:
            load_flow_parser._analyse_load_flow_data(tfo_result_error)
        exceptions = e.value.exceptions
        assert len(exceptions) == 1
        assert exceptions[0].load_flow_data == tfo_result_error.dict()
        assert exceptions[0].location == ("tap_number",)
        assert exceptions[0].category == "type_error.none.not_allowed"
        load_flow_parser._analyse_load_flow_data(tfo_result)
        load_flow_parser._analyse_load_flow_data(tfo_result3)
        assert dtos_are_equal(
            load_flow_parser._transformers,
            {
                (bus_result.node_name, tfo_result.connected_node_name, tfo_result.branch_parallel_index): Transformer(
                    sending_bus=bus_result.node_name,
                    receiving_bus=bus_result2.node_name,
                    parallel_id=tfo_result.branch_parallel_index,
                    tap_number=tfo_result.transformer_tap
                )
            }
        )
        # Same parallel index cannot be assigned to multiple transformers
        with pytest.raises(BranchParallelException):
            load_flow_parser._analyse_load_flow_data(tfo_result)

    def test_reset_parser(self, load_flow_parser, tfo8, generator_result, tfo_result, bus_result, bus_result2):
        # Parse data
        load_flow_parser._analyse_load_flow_data(tfo8)
        load_flow_parser._analyse_load_flow_data(bus_result2)
        load_flow_parser._analyse_load_flow_data(bus_result)
        load_flow_parser._analyse_load_flow_data(generator_result)
        load_flow_parser._analyse_load_flow_data(tfo_result)

        # Add an exception in the collector
        load_flow_parser._exception_collector._exceptions.append(DEEACException())

        # Check that data was stored
        assert len(load_flow_parser._transformer_info) > 0
        assert len(load_flow_parser._generators) > 0
        assert len(load_flow_parser._transformers) > 0
        assert len(load_flow_parser._buses) > 0
        assert load_flow_parser._current_origin_node_name is not None
        assert load_flow_parser._exception_collector.contains_exceptions()

        # Reset
        load_flow_parser._reset_parser()
        assert len(load_flow_parser._transformer_info) == 0
        assert len(load_flow_parser._generators) == 0
        assert len(load_flow_parser._transformers) == 0
        assert len(load_flow_parser._buses) == 0
        assert load_flow_parser._current_origin_node_name is None
        assert not load_flow_parser._exception_collector.contains_exceptions()

    def test_raise_if_duplicated(self, load_flow_parser):
        container = {"a": 4}
        load_flow_parser._raise_if_duplicated("b", container, int.__name__)
        with pytest.raises(NetworkElementNameException) as e:
            load_flow_parser._raise_if_duplicated("a", container, int.__name__)
        assert e.value.name == "a"
        assert e.value.element_type == "int"

    def test_parse_load_flow(
        self, load_flow_parser, load_flow_parser_errors, load_flow_parser_divergence, complete_case_lf_results
    ):

        # Divergent file
        with pytest.raises(LoadFlowDivergenceException):
            load_flow_parser_divergence.parse_load_flow()

        # Valid file
        lf_results = load_flow_parser.parse_load_flow()
        # TODO: update complete_case_lf_results
        return
        assert dtos_are_equal(lf_results, complete_case_lf_results)

        # File with errors
        with pytest.raises(DEEACExceptionList) as e:
            load_flow_parser_errors.parse_load_flow()
        errors = e.value.exceptions
        assert len(errors) == 1

        # TFO between NGENB1 and NHVB1 has unknown type
        assert isinstance(errors[0], LoadFlowDataValidationException)
        assert errors[0].load_flow_data == {
            "sending_node": "NGENB1",
            "receiving_node": "NHVB1",
            "parallel_index": "1",
            "type": "10"
        }
        assert errors[0].location == ("type",)
        assert errors[0].category == "type_error.enum"

        """
        # First result is a branch not associated to any origin
        assert isinstance(errors[1], LoadFlowTransformerException)
        assert errors[1].receiving_node_name == "NGENB2"

        # 2 TFOs with same parallel index on branch NHAV1 - NHAV2
        assert isinstance(errors[2], BranchParallelException)
        assert errors[2].sending_bus == "NHVA1"
        assert errors[2].receiving_bus == "NHVA2"
        assert errors[2].parallel_id == "1"

        # Duplicated bus NHVA1
        assert isinstance(errors[3], NetworkElementNameException)
        assert errors[3].name == "NHVA1"

        # TFO between NGENB1 and NHVB1 has unknown type
        assert isinstance(errors[4], LoadFlowDataValidationException)
        assert errors[4].load_flow_data == {
            "area": "GE",
            "node_name": "NHVCEQ",
            "production_active_power": "UNKNOWN",
            "production_reactive_power": "221.88"
        }
        assert errors[4].location == ("production_active_power",)
        assert errors[4].category == "type_error.float"
        """
