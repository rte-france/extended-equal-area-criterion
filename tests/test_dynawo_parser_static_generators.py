"""
Tests for Dynawo generator classification between dynamic machines and static injections.
"""

from deeac.IO.dynawo.dynawo_parser import (
    DynawoData,
    DynawoGeneratorParameters,
    select_slack_generator_id,
)
from deeac.Models.bus import Bus


def test_dynawo_data_detects_usable_dynamic_generators() -> None:
    """
    Only generators with both positive inertia and transient reactance are dynamic.
    """
    data = DynawoData(
        {
            "GEN_OK": DynawoGeneratorParameters(
                inertia_constant=4.5,
                direct_transient_reactance_pu=0.2,
                rated_apparent_power=500.0,
                machine_side_voltage=24.0,
            ),
            "GEN_NO_H": DynawoGeneratorParameters(
                inertia_constant=None,
                direct_transient_reactance_pu=0.2,
                rated_apparent_power=500.0,
                machine_side_voltage=24.0,
            ),
            "GEN_NO_X": DynawoGeneratorParameters(
                inertia_constant=4.5,
                direct_transient_reactance_pu=None,
                rated_apparent_power=500.0,
                machine_side_voltage=24.0,
            ),
            "GEN_ZERO_H": DynawoGeneratorParameters(
                inertia_constant=0.0,
                direct_transient_reactance_pu=0.2,
                rated_apparent_power=500.0,
                machine_side_voltage=24.0,
            ),
        }
    )

    assert data.has_dynamic_generator("GEN_OK") is True
    assert data.has_dynamic_generator("GEN_NO_H") is False
    assert data.has_dynamic_generator("GEN_NO_X") is False
    assert data.has_dynamic_generator("GEN_ZERO_H") is False
    assert data.has_dynamic_generator("MISSING") is False


def test_select_slack_generator_ignores_ineligible_generators() -> None:
    """
    Slack selection must stay within the retained dynamic machine subset.
    """
    bus_dict = {
        "BUS_SLACK_LIKE": Bus(name="BUS_SLACK_LIKE", base_voltage=400.0, voltage_magnitude=400.0, phase_angle=0.0),
        "BUS_DYNAMIC": Bus(name="BUS_DYNAMIC", base_voltage=400.0, voltage_magnitude=400.0, phase_angle=0.1),
    }
    generators = {
        "GEN_STATIC": {"connected": True, "bus_id": "BUS_SLACK_LIKE"},
        "GEN_DYNAMIC": {"connected": True, "bus_id": "BUS_DYNAMIC"},
    }

    slack_generator_id = select_slack_generator_id(
        generators=type("FakeFrame", (), {"iterrows": lambda self: iter(generators.items())})(),
        bus_dict=bus_dict,
        eligible_generator_ids={"GEN_DYNAMIC"},
    )

    assert slack_generator_id == "GEN_DYNAMIC"
