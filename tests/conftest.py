"""
Shared test fixtures for deeac.
"""
from pathlib import Path

import pytest

from deeac.IO.eurostag.events.event_parser import EurostagEventParser
from deeac.IO.eurostag.load_flow.load_flow_parser import EurostagLoadFlowParser
from deeac.IO.eurostag.topology.topology_parser import EurostagTopologyParser


TEST_DATA_DIR = Path(__file__).parent / "data"
CASE1_DIR = TEST_DATA_DIR / "case1"


@pytest.fixture
def case1_topology():
    """
    Build the case1 network topology.
    """
    parser = EurostagTopologyParser(
        ech_file=str(CASE1_DIR / "case1.ech"),
        dta_file=str(CASE1_DIR / "case1.dta"),
    )
    return parser.parse_network_topology()


@pytest.fixture
def case1_network(case1_topology):
    """
    Build the full case1 network with load-flow applied.
    """
    load_flow_parser = EurostagLoadFlowParser(load_flow_results_file=str(CASE1_DIR / "case1.lf"))
    load_flow_parser.parse_load_flow(case1_topology)
    return case1_topology


@pytest.fixture
def case1_event_parser():
    """
    Return the event parser for the case1 line fault.
    """
    return EurostagEventParser(
        eurostag_event_file=str(CASE1_DIR / "case1_line.seq"),
        protection_delay=0.0,
    )
