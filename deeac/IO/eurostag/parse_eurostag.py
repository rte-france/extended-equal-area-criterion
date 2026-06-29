"""
Module for parse_eurostag.

:module: parse_eurostag
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.
from typing import Optional, Sequence

from deeac.IO.event_loader import EventLoader
from deeac.IO.eurostag.events.event_parser import EurostagEventParser
from deeac.IO.eurostag.topology.topology_parser import EurostagTopologyParser
from deeac.IO.eurostag.load_flow.load_flow_parser import EurostagLoadFlowParser
from deeac.Models.events.fault_events import FaultEvents
from deeac.Models.network import Network


def parse_eurostag(
    ech_file: str,
    dta_file: str,
    lf_file: str,
    seq_file: Optional[str] = None,
    seq_files: Optional[Sequence[str]] = None,
    protection_delay: float = 0.0,
) -> Network:
    """
    
    :param ech_file:
    :param dta_file:
    :param lf_file:
    :param seq_file:
    :param seq_files:
    :param protection_delay:
    :return:
    """
    topology_parser = EurostagTopologyParser(
        ech_file=ech_file,
        dta_file=dta_file
    )
    load_flow_parser = EurostagLoadFlowParser(
        load_flow_results_file=lf_file
    )

    # Parse network topology and load flow data
    network = topology_parser.parse_network_topology()
    load_flow_parser.parse_load_flow(network=network)

    seq_paths: Sequence[str] = []
    if seq_file is not None:
        seq_paths = [seq_file]
    elif seq_files is not None:
        seq_paths = list(seq_files)

    fault_events = []
    for seq_path in seq_paths:
        event_parser = EurostagEventParser(
            eurostag_event_file=seq_path,
            protection_delay=protection_delay,
        )
        loader = EventLoader(event_parser=event_parser)
        failure_events, mitigation_events = loader.load_events()
        short_circuit_delay = None
        if failure_events and mitigation_events:
            short_circuit_delay = event_parser.short_circuit_delay
        fault_events.append(
            FaultEvents(
                failure_events=failure_events,
                mitigation_events=mitigation_events,
                name=event_parser.name,
                short_circuit_delay=short_circuit_delay,
            )
        )
    network.set_fault_events(fault_events)
    return network
