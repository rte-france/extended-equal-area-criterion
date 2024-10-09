# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import List
from pydantic import ValidationError

from deeac.domain.exceptions import DEEACExceptionList, DEEACExceptionCollector
from .dtos import NetworkData
from .exceptions import IncompleteNetworkDataException, NetworkDataValidationException
from .record_description import RecordDescription


class NetworkDataDescription:
    """
    Description of network data that can be found in an Eurostag file.
    Network data represents mostly one network element (e.g. a transformer or line), and gathers one or several records.
    A network data description contains one or multiple record descriptions, and gives the maximum number of records
    (i.e. lines) that can be associated to this network data (-1 means unbounded). It also specifies the kind of
    NetworkData it describes.
    """

    def __init__(self, max_nb_records: int, record_descriptions: List[RecordDescription], network_data: NetworkData):
        """
        Initialization.

        :param max_nb_records: Maximum number of records for this network data.
        :param record_descriptions: List of the descriptions of each record in this network data.
        :param network_data: NetworkData object associated to this description.
        """
        self.max_nb_records = max_nb_records
        self.record_descriptions = record_descriptions
        self.network_data = network_data

    def parse_network_data(self, network_data_records: List[str]) -> NetworkData:
        """
        Parse network data based on a list of its records.

        :param network_data_records: A list of records corresponding to the network data.
        :return: A NetworkData object.
        :raise: DEEACExceptionList in case of errors.
        """
        exception_collector = DEEACExceptionCollector()

        # Check if incomplete data
        try:
            self.raise_for_incomplete_data(network_data_records)
        except IncompleteNetworkDataException as e:
            raise DEEACExceptionList([e])

        nb_descriptions = len(self.record_descriptions)
        last_description_index = nb_descriptions - 1
        # Data extracted from all the records associated to this network data
        records_data = {}
        if self.max_nb_records == -1:
            # Last record description may be used for multiple records -> corresponding data stored in a list
            records_data[self.record_descriptions[-1].list_name] = list()

        for index, record in enumerate(network_data_records):
            with exception_collector:
                # Get record description taking into account last records may have the same description
                record_description = self.record_descriptions[min(index, last_description_index)]
                record_description.raise_for_unexpected_length(record)

                # Parse record and extract its data
                record_data = record_description.parse_record(record)

                if self.max_nb_records == -1 and index >= last_description_index:
                    # Last records must be stored in a list
                    records_data[record_description.list_name].append(record_data)
                else:
                    records_data = {**records_data, **record_data}
        exception_collector.raise_for_exception()

        try:
            return self.network_data(**records_data)
        except ValidationError as e:
            exception_list = DEEACExceptionList()
            # Get validation errors and create corresponding DEEAC exceptions
            for val_error in e.errors():
                exception_list.append(
                    NetworkDataValidationException(network_data_records, val_error["loc"], val_error["type"])
                )
            raise(exception_list)

    def raise_for_incomplete_data(self, network_data_records: List[str]):
        """
        Raise an exception if the record data does not contain the expected number of records.

        :param record: The record data to check.
        :raise IncompleteNetworkDataException if the data does not contain the exêcted number or records.
        """
        nb_descriptions = len(self.record_descriptions)
        nb_records = len(network_data_records)
        if nb_records < nb_descriptions or (self.max_nb_records != -1 and nb_records > nb_descriptions):
            raise IncompleteNetworkDataException(network_data_records, nb_records, nb_descriptions, self.max_nb_records)
