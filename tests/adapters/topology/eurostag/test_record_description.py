# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest

from deeac.adapters.topology.eurostag.exceptions import UnexpectedRecordLengthException
from deeac.adapters.topology.eurostag.record_description import RecordDescription


class TestRecordDescription:

    def test_raise_unexpected_record_length(self, cd_record_description, first_cd_record, invalid_cd_record):
        # Correct length
        cd_record_description.raise_for_unexpected_length(first_cd_record)

        # Bad length
        with pytest.raises(UnexpectedRecordLengthException):
            cd_record_description.parse_record(invalid_cd_record)

    def test_parse_record(self, cd_record_description, first_cd_record, second_cd_record, invalid_cd_record):
        # Complete record
        parsed_record = cd_record_description.parse_record(first_cd_record)
        assert len(parsed_record) == 4
        assert parsed_record["sending_node"] == "NODE23"
        assert parsed_record["opening_code"] == "-"
        assert parsed_record["receiving_node"] == "NODE2409"
        assert parsed_record["parallel_index"] == "A"

        # Record with empty fields
        parsed_record = cd_record_description.parse_record(second_cd_record)
        assert len(parsed_record) == 4
        assert parsed_record["sending_node"] == "NODE23"
        assert parsed_record["opening_code"] is None
        assert parsed_record["receiving_node"] == "NODE2409"
        assert parsed_record["parallel_index"] == "A"

        # Record not the format (bad length)
        with pytest.raises(UnexpectedRecordLengthException):
            cd_record_description.parse_record(invalid_cd_record)

        # Partial and non-mandatory record
        rdesc = RecordDescription(
            min_length=38,
            max_length=47,
            format={
                'sending_node': (2, 10),
                'opening_code': (10, 11),
                'receiving_node': (11, 19),
                'parallel_index': (19, 20),
                'partial': (38, 42),
                'not_mandatory': (42, 47)
            }
        )
        parsed_record = rdesc.parse_record("6 NODE23  -NODE2409A       0.       0.p")
        assert parsed_record["partial"] == "p"
        assert parsed_record["not_mandatory"] is None
