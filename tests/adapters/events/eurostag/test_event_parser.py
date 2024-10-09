# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest

from deeac.adapters.events.eurostag.exceptions import EventDataValidationException
from deeac.domain.exceptions import DEEACExceptionList, DEEACExternalException


class TestEventParser:

    def test_parse_events(self, event_file_parser, event_file_parser_errors, complete_case_events):
        events = event_file_parser.parse_events()
        assert events == complete_case_events

        with pytest.raises(DEEACExceptionList) as e:
            event_file_parser_errors.parse_events()
        errors = e.value.exceptions
        assert len(errors) == 2

        # Bad breaker position
        assert isinstance(errors[0], EventDataValidationException)
        assert errors[0].location == ("position",)
        assert errors[0].category == "type_error.enum"

        # Unimplemented
        assert isinstance(errors[1], DEEACExternalException)
        assert errors[1].exception_type == NotImplementedError
