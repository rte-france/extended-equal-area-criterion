# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from deeac.adapters.topology.eurostag import EchRecordType
from tests.adapters.dto_comparators import dtos_are_equal


class TestEchFileParser:

    def test_get_record_number(self, ech_file_parser, tfo8_records, first_cd_record):
        # The two last records have the same number
        expected_record_numbers = [1, 2, 3, 3]
        for i, record in enumerate(tfo8_records):
            nb = ech_file_parser._get_record_number(EchRecordType.TYPE8_TRANSFORMER, record)
            assert nb == expected_record_numbers[i]
            # Update record for consistency
            ech_file_parser._prev_record_type = EchRecordType.TYPE8_TRANSFORMER
            ech_file_parser._prev_record_nb = nb

        # Try again with same type of record and see that the parser saw a new record
        for i, record in enumerate(tfo8_records):
            nb = ech_file_parser._get_record_number(EchRecordType.TYPE8_TRANSFORMER, record)
            assert nb == expected_record_numbers[i]
            # Update record for consistency
            ech_file_parser._prev_record_type = EchRecordType.TYPE8_TRANSFORMER
            ech_file_parser._prev_record_nb = nb

        #  Try another type of record
        for _ in range(0, 2):
            assert ech_file_parser._get_record_number(EchRecordType.COUPLING_DEVICE, first_cd_record) == 1
            # Update record for consistency
            ech_file_parser._prev_record_type = EchRecordType.COUPLING_DEVICE
            ech_file_parser._prev_record_nb = nb
            assert ech_file_parser._get_record_number(EchRecordType.COUPLING_DEVICE, first_cd_record) == 1

    def test_identify_record(
        self, ech_file_parser, tfo8_records, first_cd_record, invalid_cd_record, not_of_interest_record
    ):
        # Check if all records of a type-8 transformer are recognized (2 times)
        for _ in range(0, 2):
            expected_record_numbers = [1, 2, 3, 3]
            for i, record in enumerate(tfo8_records):
                (rtype, rnb) = ech_file_parser._identify_record(record)
                assert rtype == EchRecordType.TYPE8_TRANSFORMER
                assert rnb == expected_record_numbers[i]

        # Check coupling device is recognized
        (rtype, rnb) = ech_file_parser._identify_record(first_cd_record)
        assert rtype == EchRecordType.COUPLING_DEVICE
        assert rnb == 1

        # Check with a record which is not of interest
        assert ech_file_parser._identify_record(not_of_interest_record) is None

    def test_parse_ech_file(self, ech_file_parser, complete_case_ech_content):
        # Parse file
        ech_file_parser.parse_file()
        # Get static data and check values
        record_types = [rt for rt in ech_file_parser.file_description]
        for rt in record_types:
            assert dtos_are_equal(complete_case_ech_content[rt], ech_file_parser.get_network_data(rt))
