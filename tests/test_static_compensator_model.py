"""
Tests for static compensator numerical representation.
"""
from pathlib import Path

import numpy as np

from deeac.IO.eurostag.parse_eurostag import parse_eurostag
from deeac.Models.capacitor_bank import CapacitorBank
from deeac.Models.network import Network


def parse_svc_example() -> Network:
    """
    Parse the Eurostag SVC example.

    The case_5_c fixture contains one SVC and a solved load-flow result. It is
    intentionally used as a regression for #32 because the accepted first model
    is the existing admittance-injection approximation, not a new dynamic
    STATCOM model.

    :return: Parsed network.
    """
    case_dir: Path = Path(__file__).resolve().parents[1] / "examples" / "eurostag_cases" / "case_5_c---svc"
    return parse_eurostag(
        ech_file=str(case_dir / "fech_svc.ech"),
        dta_file=str(case_dir / "fdta.dta"),
        lf_file=str(case_dir / "fech_svc.lf"),
    )


def test_eurostag_svc_stays_admittance_injection() -> None:
    """
    Keep the current SVC/STATCOM approximation explicit.

    The parser stores the SVC as a ``CapacitorBank`` and the load-flow parser
    converts the solved reactive output into an admittance. This is the
    behaviour requested for #32 "for now"; richer STATCOM dynamics can be added
    later behind a separate model option without breaking this baseline.
    """
    network: Network = parse_svc_example()
    svc: CapacitorBank = network.svc_map["CSPCHV 1"]

    assert isinstance(svc, CapacitorBank)
    assert np.isclose(svc.reactive_power, -134.88)
    assert abs(svc.admittance) > 0.0
    assert svc in svc.bus.capacitor_banks
