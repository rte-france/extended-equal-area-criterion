# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest

from deeac.domain.exceptions import DEEACExceptionList
from deeac.adapters.eeac_tree.json.exceptions import JSONParsingException, EACTreeDataValidationException


class TestJSONTreeParser:

    def test_parse_execution_tree(
        self, json_tree_parser, json_tree_parser_parsing_error, json_tree_parser_content_error, basic_domib_eeac_tree
    ):
        # Complete basic tree
        tree = json_tree_parser.parse_execution_tree()
        assert tree == basic_domib_eeac_tree

        # Parsing error
        with pytest.raises(DEEACExceptionList) as error_list:
            json_tree_parser_parsing_error.parse_execution_tree()
        errors = error_list.value.exceptions
        assert len(errors) == 1
        exception = errors[0]
        assert type(exception) == JSONParsingException
        assert exception.msg == "Expecting property name enclosed in double quotes"
        assert (exception.row, exception.column) == (10, 13)

        # Content error
        with pytest.raises(DEEACExceptionList) as error_list:
            json_tree_parser_content_error.parse_execution_tree()
        errors = error_list.value.exceptions
        assert len(errors) == 9
        threshold_exception = errors[0]
        assert type(threshold_exception) == EACTreeDataValidationException
        assert threshold_exception.location == ("root", "configuration", "threshold")
        assert threshold_exception.category == "type_error.float"
        type_exception = errors[-1]
        assert type(type_exception) == EACTreeDataValidationException
        assert type_exception.location == ("root", "children", 0, "type")
        assert type_exception.category == "value_error.missing"
        for error in errors[1:-1]:
            # Other errors are generated because the parser could not identify the Evaluator type
            assert type(error) == EACTreeDataValidationException
            assert error.category == "value_error.missing"
