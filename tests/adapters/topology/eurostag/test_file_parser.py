# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest

from deeac.adapters.topology.eurostag import DtaRecordType
from deeac.adapters.topology.eurostag.dtos import GeneratorDynamicPart
from deeac.adapters.topology.eurostag.exceptions import (
    IncompleteNetworkDataException, NetworkDataValidationException, UnexpectedRecordLengthException
)
from deeac.domain.exceptions import DEEACExceptionList, DEEACException


class TestFileParser:

    def test_add_record(self, file_parser, dyn_gen_records, not_of_interest_record):
        # Record not added because missing previous records
        file_parser._add_record(dyn_gen_records[4])
        assert len(file_parser._file_records) == 0

        # Not-of-interest record
        file_parser._add_record(not_of_interest_record)
        assert len(file_parser._file_records) == 0

        # Add expected records
        for i, record in enumerate(dyn_gen_records):
            file_parser._add_record(record)
            assert len(file_parser._file_records) == 1
            expected_records = [[rec for rec in dyn_gen_records[0:i + 1]]]
            assert file_parser._file_records[DtaRecordType.FULL_EXTERNAL_PARAM_GENERATOR] == expected_records

        # Add new record of same type
        file_parser._add_record(dyn_gen_records[0])
        assert len(file_parser._file_records) == 1
        expected_records = [dyn_gen_records, [dyn_gen_records[0]]]
        assert file_parser._file_records[DtaRecordType.FULL_EXTERNAL_PARAM_GENERATOR] == expected_records

    def test_parse_network_data(self, file_parser, dyn_gen_records):
        # No record
        file_parser._parse_network_data()
        assert len(file_parser._file_network_data) == 0

        # Add records for two generators
        for _ in range(0, 2):
            for i, record in enumerate(dyn_gen_records):
                file_parser._add_record(record)

        # Parse data
        file_parser._parse_network_data()

        # Check
        assert len(file_parser._file_network_data[DtaRecordType.FULL_EXTERNAL_PARAM_GENERATOR]) == 2
        generators = file_parser._file_network_data[DtaRecordType.FULL_EXTERNAL_PARAM_GENERATOR]
        for gen in generators:
            assert isinstance(gen, GeneratorDynamicPart)

        # Reset parser
        file_parser._reset_parser()

        # Add incomplete data
        file_parser._add_record(dyn_gen_records[0])

        # Parse data
        file_parser._parse_network_data()
        assert len(file_parser._exception_collector._exceptions) == 1
        assert isinstance(file_parser._exception_collector._exceptions[0], IncompleteNetworkDataException)

    def test_reset_parser(self, file_parser, dyn_gen_records):
        # Add records for a generators
        for i, record in enumerate(dyn_gen_records):
            file_parser._add_record(record)
        # Parse data
        file_parser._parse_network_data()
        # Add an exception in the collector
        file_parser._exception_collector._exceptions.append(DEEACException())

        # Check that data was stored
        assert len(file_parser._file_network_data) > 0
        assert len(file_parser._file_records) > 0
        assert file_parser._exception_collector.contains_exceptions()

        # Reset
        file_parser._reset_parser()
        assert len(file_parser._file_network_data) == 0
        assert len(file_parser._file_records) == 0
        assert not file_parser._exception_collector.contains_exceptions()

    def test_get_network_data(self, file_parser, dyn_gen_records):
        # No record found
        assert file_parser.get_network_data(DtaRecordType.FULL_EXTERNAL_PARAM_GENERATOR) == []

        # Add records for two generators
        for _ in range(0, 2):
            for i, record in enumerate(dyn_gen_records):
                file_parser._add_record(record)
        # Parse data
        file_parser._parse_network_data()
        generators = file_parser.get_network_data(DtaRecordType.FULL_EXTERNAL_PARAM_GENERATOR)
        assert len(generators) == 2
        for gen in generators:
            assert isinstance(gen, GeneratorDynamicPart)

    def test_parse_file(self, file_parser, file_parser_errors):
        file_parser.parse_file()
        generators = file_parser.get_network_data(DtaRecordType.FULL_EXTERNAL_PARAM_GENERATOR)
        assert len(generators) == 4
        for gen in generators:
            assert isinstance(gen, GeneratorDynamicPart)

        with pytest.raises(DEEACExceptionList) as e:
            file_parser_errors.parse_file()
        assert len(e.value.exceptions) == 3
        assert isinstance(e.value.exceptions[0], NetworkDataValidationException)
        assert e.value.exceptions[0].location == ('inertia_constant',)
        assert isinstance(e.value.exceptions[1], UnexpectedRecordLengthException)
        assert isinstance(e.value.exceptions[2], IncompleteNetworkDataException)
