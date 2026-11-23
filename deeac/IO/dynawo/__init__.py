"""Dynawo input parsing helpers with an optional PowSyBl dependency."""

from typing import Optional

from deeac.Models.network import Network
from deeac.enums import HvdcElectricalModel

__all__ = ["parse_dynawo"]


def parse_dynawo(
    jobs_file: Optional[str],
    iidm_file: Optional[str],
    dyd_file: Optional[str],
    par_file: Optional[str],
    dotted_generator_inertia_multiplier: float = 1.0,
    hvdc_model: HvdcElectricalModel = HvdcElectricalModel.LOAD,
) -> Network:
    """Parse Dynawo input files, loading PowSyBl only when requested.

    :param jobs_file: Optional Dynawo jobs file path.
    :param iidm_file: Optional IIDM network path.
    :param dyd_file: Optional DYD dynamic-model path.
    :param par_file: Optional PAR parameter path.
    :param dotted_generator_inertia_multiplier: Inertia multiplier for dotted
        generator IDs.
    :param hvdc_model: Electrical model assigned to HVDC converters.
    :return: Parsed Dynawo network.
    """
    from deeac.IO.dynawo.parse_dynawo import parse_dynawo as parse_dynawo_impl

    return parse_dynawo_impl(
        jobs_file=jobs_file,
        iidm_file=iidm_file,
        dyd_file=dyd_file,
        par_file=par_file,
        dotted_generator_inertia_multiplier=dotted_generator_inertia_multiplier,
        hvdc_model=hvdc_model,
    )
