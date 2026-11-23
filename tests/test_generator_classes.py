"""
Focused tests for the current generator and bus model.
"""
from deeac.Models.branch import Branch
from deeac.Models.bus import Bus
from deeac.Models.generator import SynchronousGenerator
from deeac.Models.line import Line
from deeac.Models.network import SimplifiedNetwork
from deeac.enums import BusType, GeneratorType


def test_generator_attached_to_pv_bus_keeps_bus_type() -> None:
    """
    A PV generator should make an otherwise implicit bus behave as PV.
    """
    bus = Bus(
        name="N1",
        base_voltage=100.0,
        voltage_magnitude=100.0,
        phase_angle=0.0,
        tpe=None,
    )

    generator = SynchronousGenerator(
        name="GEN1",
        tpe=GeneratorType.PV,
        bus=bus,
        direct_transient_reactance=20.0,
        inertia_constant=4.0,
        active_power=50.0,
        max_active_power=60.0,
        reactive_power=10.0,
    )

    bus.add_generator(generator)

    assert bus.type == BusType.PV


def test_generator_internal_voltage_is_computed_on_creation() -> None:
    """
    The current generator model should compute a non-zero internal voltage.
    """
    bus = Bus(
        name="N2",
        base_voltage=100.0,
        voltage_magnitude=100.0,
        phase_angle=0.0,
        tpe=BusType.PV,
    )

    generator = SynchronousGenerator(
        name="GEN2",
        tpe=GeneratorType.PV,
        bus=bus,
        direct_transient_reactance=15.0,
        inertia_constant=3.5,
        active_power=40.0,
        max_active_power=45.0,
        reactive_power=5.0,
    )

    assert generator.internal_voltage != 0j
    assert generator.rotor_angle is not None


def test_reduced_admittance_keeps_two_generator_buses() -> None:
    """
    Generator buses should remain explicit in the reduced admittance matrix.
    """
    first_bus = Bus(name="GEN_BUS_1", base_voltage=100.0, voltage_magnitude=100.0, phase_angle=0.0)
    second_bus = Bus(name="GEN_BUS_2", base_voltage=100.0, voltage_magnitude=100.0, phase_angle=0.0)

    first_generator = SynchronousGenerator(
        name="GEN1",
        tpe=GeneratorType.PV,
        bus=first_bus,
        direct_transient_reactance=20.0,
        inertia_constant=4.0,
        active_power=60.0,
        max_active_power=80.0,
        reactive_power=10.0,
    )
    second_generator = SynchronousGenerator(
        name="GEN2",
        tpe=GeneratorType.PV,
        bus=second_bus,
        direct_transient_reactance=25.0,
        inertia_constant=5.0,
        active_power=30.0,
        max_active_power=35.0,
        reactive_power=5.0,
    )

    first_bus.add_generator(first_generator)
    second_bus.add_generator(second_generator)

    line = Line(
        base_impedance=100.0,
        resistance=1.0,
        reactance=10.0,
        shunt_conductance=0.0,
        shunt_susceptance=0.0,
    )
    branch = Branch(first_bus=first_bus, second_bus=second_bus)
    branch.parallel_elements["1"] = line
    first_bus.add_branch(branch)
    second_bus.add_branch(branch)

    network = SimplifiedNetwork(buses=[first_bus, second_bus])
    reduced_matrix, bus_index_map = network.get_reduced_admittance_dense()

    assert reduced_matrix.shape == (2, 2)
    assert bus_index_map == dict(GEN_BUS_1=0, GEN_BUS_2=1)
