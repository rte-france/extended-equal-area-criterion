# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest

from deeac.adapters.load_flow.eurostag.exceptions import LoadFlowDataValidationException
from deeac.domain.exceptions import DEEACExceptionList
from tests.adapters.dto_comparators import dtos_are_equal


class TestTableDescription:

    def test_parse_transformer_row(self, tfo_table_description, tfo1, tfo5, tfo8):
        # Row with 2 transformers
        row = " |    NGENB1   |  NHVA1      | 2 |       1.0 |   1|      NGEN A1  | NHVB1      | 1 |      1.10 |   8|"
        tfos = tfo_table_description.parse_row(row)
        assert len(tfos) == 2
        assert dtos_are_equal(tfos[0], tfo1)
        assert dtos_are_equal(tfos[1], tfo8)

        # Row with 1 transformer
        row = " |    NGENA2   |  NH VA 2    | 1 |      1.10 |   145|               |            |   |           |    |"
        tfos = tfo_table_description.parse_row(row)
        assert len(tfos) == 1
        assert dtos_are_equal(tfos[0], tfo5)

        # Bad transformer type, missing parallel index
        row = " |    NGENA2   |  NH VA 2    |   |      1.10 |   105|               |            |   |           |    |"
        with pytest.raises(DEEACExceptionList) as e:
            tfos = tfo_table_description.parse_row(row)
        assert len(e.value.exceptions) == 2
        for exc in e.value.exceptions:
            assert isinstance(exc, LoadFlowDataValidationException)
        assert e.value.exceptions[0].location == ('parallel_index',)
        assert e.value.exceptions[0].category == "value_error.missing"
        assert e.value.exceptions[1].location == ('type',)
        assert e.value.exceptions[1].category == "type_error.enum"

    def test_parse_nodes_row(self, results_table_description, bus_result):
        row = " |A  NGEN A1 | 24.00 -15.17|  900.00   322.12|     0.00      0.00|             |                |      "\
              "      |                |     |"
        result = results_table_description.parse_row(row)
        assert dtos_are_equal(result[0], bus_result)

    def test_parse_hvdc_converter_row(self, hvdc_converter_table_description, hvdc_converter_result):
        row = "    | CONV 1   | DCNODE 1 | GROUND   | BUSNODE1 |V|V|  900.00 |  322.12 |   -1.56 |  640.00 |  412.49 |"\
              "   -6.32 |    0.00 |"
        result = hvdc_converter_table_description.parse_row(row)
        assert dtos_are_equal(result[0], hvdc_converter_result)

    def test_parse_results_row(self, results_table_description, bus_result, tfo_result, svc_result):
        # Bus-type results
        row = " |A  NGEN A1 | 24.00 -15.17|  900.00   322.12|     0.00      0.00|             |                |      "\
              "      |                |     |"
        results = results_table_description.parse_row(row)
        assert len(results) == 1
        assert dtos_are_equal(results[0], bus_result)

        # TFO-type results with None pattern
        row = "|     ////  |             |                 |                   |A  NHVB1    1|   314.8    66.1|  0.4 "\
              "  10.9|  321.7 1000  32|   9 |"
        results = results_table_description.parse_row(row)
        assert len(results) == 1
        assert dtos_are_equal(results[0], tfo_result)

        # SVC-type results
        row = " |SV SVC_1   |             |             0.05|                   |             |                |     "\
              "       |                |     |"
        results = results_table_description.parse_row(row)
        assert len(results) == 1
        assert dtos_are_equal(results[0], svc_result)
