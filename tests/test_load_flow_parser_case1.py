"""
Tests for Eurostag load-flow parsing using the case1 fixtures.
"""
import numpy as np


def test_case1_load_flow_updates_slack_bus(case1_network):
    """
    Confirm that load-flow data updates the slack bus voltage.
    """
    slack_bus = case1_network.get_bus("NHVCEQ")
    assert np.isclose(slack_bus.voltage_magnitude, 380.0)
    assert np.isclose(slack_bus.phase_angle, 0.0)


def test_case1_load_flow_updates_generator(case1_network):
    """
    Confirm that generator powers and internal voltage are updated.
    """
    generator = next(gen for gen in case1_network.generators if gen.name == "GENA1")
    assert np.isclose(generator.active_power, 900.0)
    assert np.isclose(generator.reactive_power, 322.12)
    assert abs(generator.internal_voltage) > 0.0
