"""
Tests for simplified network creation using a small synthetic network.
"""
from deeac.Models.bus import Bus
from deeac.Models.generator import Generator
from deeac.Models.line import Line
from deeac.Models.network import Network, NetworkComputed
from deeac.Models.constants import BASE_POWER
from deeac.enums import BusType, GeneratorType, NetworkState


def build_simple_network() -> Network:
    """
    Build a small network with one disconnected bus and one generator.
    """
    network = Network(base_power=BASE_POWER)

    bus_a = Bus(
        name="A",
        base_voltage=100.0,
        voltage_magnitude=100.0,
        phase_angle=0.0,
        tpe=BusType.SLACK,
    )
    bus_b = Bus(name="B", base_voltage=100.0, voltage_magnitude=100.0, phase_angle=0.0)
    bus_c = Bus(name="C", base_voltage=100.0, voltage_magnitude=100.0, phase_angle=0.0)

    network.add_bus(bus_a)
    network.add_bus(bus_b)
    network.add_bus(bus_c)

    base_impedance = bus_a.base_voltage ** 2 / BASE_POWER
    line_ab = Line(
        base_impedance=base_impedance,
        resistance=0.0,
        reactance=10.0,
        shunt_conductance=0.0,
        shunt_susceptance=0.0,
        closed_at_first_bus=True,
        closed_at_second_bus=True,
    )
    network.add_branch(bus_a, bus_b, line_ab, "1")

    line_bc = Line(
        base_impedance=base_impedance,
        resistance=0.0,
        reactance=10.0,
        shunt_conductance=0.0,
        shunt_susceptance=0.0,
        closed_at_first_bus=False,
        closed_at_second_bus=False,
    )
    network.add_branch(bus_b, bus_c, line_bc, "1")

    generator = Generator(
        name="G1",
        bus=bus_a,
        tpe=GeneratorType.SLACK,
        direct_transient_reactance=0.1,
        inertia_constant=5.0,
        active_power=100.0,
        max_active_power=200.0,
        reactive_power=20.0,
    )
    network.add_generator(generator)
    return network


def test_simplified_network_discards_disconnected_bus():
    """
    Confirm that disconnected buses are removed from the simplified network.
    """
    network = build_simple_network()
    computed = NetworkComputed()
    network.initialize_simplified_network(computed)

    simplified = network.get_state(computed, NetworkState.PRE_FAULT)
    assert "C" in simplified.disconnected_buses

    simplified_bus_names = {bus.name for bus in simplified.network.buses}
    assert "A" in simplified_bus_names
    assert "B" in simplified_bus_names
    assert "C" not in simplified_bus_names


def test_simplified_network_adds_fictive_generator_bus():
    """
    Confirm that generators are moved to fictive internal-voltage buses.
    """
    network = build_simple_network()
    computed = NetworkComputed()
    network.initialize_simplified_network(computed)

    simplified = network.get_state(computed, NetworkState.PRE_FAULT)
    generator = simplified.network.generators[0]
    assert generator.bus.type == BusType.GEN_INT_VOLT
    assert generator.bus.name.startswith("INTERNAL_VOLTAGE_G1")
