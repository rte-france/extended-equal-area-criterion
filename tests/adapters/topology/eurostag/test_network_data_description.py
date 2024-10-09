# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest

from deeac.adapters.topology.eurostag.exceptions import (
    IncompleteNetworkDataException, UnexpectedRecordLengthException, NetworkDataValidationException
)
from deeac.domain.exceptions import DEEACExceptionList
from tests.adapters.dto_comparators import dtos_are_equal


class TestNetworkDataDescription:

    def test_raise_for_incomplete_data(self, cd_network_data_description, first_cd_record, second_cd_record):
        # Correct number of records
        cd_network_data_description.raise_for_incomplete_data([first_cd_record])

        # Incorrect number of records
        with pytest.raises(IncompleteNetworkDataException):
            cd_network_data_description.raise_for_incomplete_data([first_cd_record, second_cd_record])
        with pytest.raises(IncompleteNetworkDataException):
            cd_network_data_description.raise_for_incomplete_data([])

        # Unbound maximum number of records for test purpose
        cd_network_data_description.max_nb_records = -1
        cd_network_data_description.raise_for_incomplete_data([first_cd_record, second_cd_record])
        cd_network_data_description.max_nb_records = 1

    def test_parse_network_data(
        self, cd_network_data_description, cd_open_network_data, cd_closed_network_data, tfo8_network_data_description,
        tfo8_static_network_data, dyn_gen_network_data_description, dyn_gen_network_data, first_cd_record,
        second_cd_record, invalid_cd_record, invalid_data_format_cd_record, tfo8_records, dyn_gen_records
    ):
        # Parse simple and complete coupling device
        coupling_device = cd_network_data_description.parse_network_data([first_cd_record])
        assert dtos_are_equal(coupling_device, cd_open_network_data)

        # Parse coupling device with closed opening code (blank input)
        coupling_device = cd_network_data_description.parse_network_data([second_cd_record])
        assert dtos_are_equal(coupling_device, cd_closed_network_data)

        # Network data with multiple records of same format
        tfo8 = tfo8_network_data_description.parse_network_data(tfo8_records)
        assert dtos_are_equal(tfo8, tfo8_static_network_data)

        # Dynamic data of a generator
        gen = dyn_gen_network_data_description.parse_network_data(dyn_gen_records)
        assert dtos_are_equal(gen, dyn_gen_network_data)

        # Parse incomplete network metadata
        with pytest.raises(DEEACExceptionList) as e:
            # Bad record length
            cd_network_data_description.parse_network_data([invalid_cd_record])
        assert len(e.value.exceptions) == 1
        assert isinstance(e.value.exceptions.pop(), UnexpectedRecordLengthException)
        with pytest.raises(DEEACExceptionList) as e:
            # Too much records
            cd_network_data_description.parse_network_data([first_cd_record, second_cd_record])
        assert len(e.value.exceptions) == 1
        assert isinstance(e.value.exceptions.pop(), IncompleteNetworkDataException)
        with pytest.raises(DEEACExceptionList) as e:
            # Data validation (Omitted source node, bad opening code)
            cd_network_data_description.parse_network_data([invalid_data_format_cd_record])
        assert len(e.value.exceptions) == 2
        for exc in e.value.exceptions:
            assert isinstance(exc, NetworkDataValidationException)
        assert e.value.exceptions[0].location == ('sending_node',)
        assert e.value.exceptions[0].category == "type_error.none.not_allowed"
        assert e.value.exceptions[1].location == ('opening_code',)
        assert e.value.exceptions[1].category == "type_error.enum"
