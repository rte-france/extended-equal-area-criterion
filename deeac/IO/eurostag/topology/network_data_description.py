"""
Module for network_data_description.

:module: network_data_description
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List, Dict

from deeac.IO.eurostag.topology.record_description import RecordDescription


class NetworkDataDescription:
    """
    Networkdatadescription.
    
    Rationale:
        This class handles input parsing or configuration shaping. It converts
        external data into the explicit objects consumed by the EEAC pipeline.
    
    :ivar max_nb_records: max nb records.
    :ivar record_descriptions: record descriptions.
    """

    def __init__(self, max_nb_records: int, record_descriptions: List[RecordDescription]):
        """
        Initialization.
        
        :param max_nb_records: Maximum number of records for this network data.
        :param record_descriptions: List of the descriptions of each record in this network data.
        """
        self.max_nb_records = max_nb_records
        self.record_descriptions = record_descriptions

    def parse_network_data(self, network_data_records: List[str]) -> Dict:
        """
        Parse network data based on a list of its records.
        
        :param network_data_records: A list of records corresponding to the network data.
        :return: A NetworkData object.
        :raise: DEEACExceptionList in case of errors.
        """
        # Check if incomplete data
        try:
            self.raise_for_incomplete_data(network_data_records)
        except ValueError as e:
            raise ValueError(str(e)) from e

        nb_descriptions = len(self.record_descriptions)
        last_description_index = nb_descriptions - 1
        # Data extracted from all the records associated to this network data
        records_data = {}
        if self.max_nb_records == -1:
            # Last record description may be used for multiple records -> corresponding data stored in a list
            records_data[self.record_descriptions[-1].list_name] = list()

        for index, record in enumerate(network_data_records):
            # Get record description taking into account last records may have the same description
            record_description = self.record_descriptions[min(index, last_description_index)]
            record_description.raise_for_unexpected_length(record)

            # Parse record and extract its data
            record_data = record_description.parse_record(record)

            if self.max_nb_records == -1 and index >= last_description_index:
                # Last records must be stored in a list
                records_data[record_description.list_name].append(record_data)
            else:
                records_data = {**records_data, **record_data} # TODO: Check magic dict

        #try:
        # return self.network_data(**records_data) # TODO: Check magic dict
        return records_data # Test this
        # except ValidationError as e:
        #     exception_list = DEEACExceptionList()
        #     # Get validation errors and create corresponding DEEAC exceptions
        #     for val_error in e.errors():
        #         exception_list.append(
        #             NetworkDataValidationException(network_data_records, val_error["loc"], val_error["type"])
        #         )
        #     raise(exception_list)

    def raise_for_incomplete_data(self, network_data_records: List[str]):
        """
        Raise an exception if the record data does not contain the expected number of records.
        
        :param network_data_records: The record data to check.
        :raise IncompleteNetworkDataException if the data does not contain the exêcted number or records.
        """
        nb_descriptions = len(self.record_descriptions)
        nb_records = len(network_data_records)
        if nb_records < nb_descriptions or (self.max_nb_records != -1 and nb_records > nb_descriptions):
            raise ValueError(
                f"Incomplete network data: got {nb_records} record(s), "
                f"expected {nb_descriptions}..{self.max_nb_records}"
            )
