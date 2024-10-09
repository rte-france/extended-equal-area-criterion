# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.adapters.topology.eurostag import DtaRecordType
from tests.adapters.dto_comparators import dtos_are_equal


class TestDtaFileParser:

    def test_identify_record(self, dta_file_parser, dyn_gen_records, not_of_interest_record):
        # Record without type before one with a type
        assert dta_file_parser._identify_record(dyn_gen_records[3]) is None

        # Check if all records of a generator are recognized (2 times)
        for _ in range(0, 2):
            for i, record in enumerate(dyn_gen_records):
                (rtype, rnb) = dta_file_parser._identify_record(record)
                assert rtype == DtaRecordType.FULL_EXTERNAL_PARAM_GENERATOR
                assert rnb == i + 1

        # Check with a record which is not of interest
        assert dta_file_parser._identify_record(not_of_interest_record) is None

    def test_parse_dta_file(self, dta_file_parser, complete_case_dta_content):
        # Parse file
        dta_file_parser.parse_file()
        # Get dynamic data and check values
        record_types = [rt for rt in dta_file_parser.file_description]
        for rt in record_types:
            assert dtos_are_equal(complete_case_dta_content[rt], dta_file_parser.get_network_data(rt))
