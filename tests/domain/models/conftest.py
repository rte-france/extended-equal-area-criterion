# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest
import math
import cmath
import numpy as np
from typing import Set

from tests import TEST_DATA_FOLDER
from deeac.adapters.load_flow.eurostag import EurostagLoadFlowParser
from deeac.adapters.topology.eurostag import EurostagTopologyParser
from deeac.adapters.events.eurostag import EurostagEventParser
from deeac.adapters.eeac_tree.json import JSONTreeParser
from deeac.services import EEACTreeLoader
from deeac.domain.services.eac import EAC
from deeac.domain.models import (
    Network, Bus, Value, PUBase, Unit, Generator, DynamicGenerator, GeneratorType, Load, FictiveLoad, Branch,
    ParallelBreakers, Breaker, Line, Transformer, GeneratorCluster, BusType, CapacitorBank, NetworkState
)
from deeac.domain.models.matrices import BusMatrix
from deeac.domain.services.critical_clusters_identifier import (
    AccelerationCriticalClustersIdentifier, CompositeCriticalClustersIdentifier, TrajectoryCriticalClustersIdentifier,
    DuringFaultTrajectoryCriticalClustersIdentifier
)
from deeac.domain.models.omib import (
    OMIBStabilityState, OMIBSwingState, ZOOMIB, RevisedZOOMIB, COOMIB, RevisedCOOMIB,
    DOMIB, RevisedDOMIB
)
from deeac.domain.models.rotor_angle_trajectory_calculator.taylor_series import GeneratorTaylorSeries
from deeac.domain.models.rotor_angle_trajectory_calculator.taylor_series import OMIBTaylorSeries
from deeac.domain.models.rotor_angle_trajectory_calculator.numerical_integrator import OMIBNumericalIntegrator
from deeac.domain.models.eeac_tree import (
    EEACTree, CriticalClustersIdentifierNode, CriticalClustersEvaluatorNode, CriticalClusterSelectorNode, OMIBNode,
    EACNode, GeneratorTrajectoryCalculatorNode, OMIBTrajectoryCalculatorNode, CriticalClustersIdentifierNodeInputs,
    CriticalClustersEvaluatorNodeInputs, OMIBTrajectoryCalculatorNodeInputs, OMIBNodeInputs, EACNodeInputs,
    GeneratorTrajectoryCalculatorNodeInputs, CriticalClusterSelectorNodeInputs, EEACClusterResults
)
from deeac.domain.ports.dtos import events as event_dtos, Value as ValueDto, Unit as UnitDto
import deeac.domain.ports.dtos.eeac_tree as tree_dtos
from deeac.services import NetworkLoader, EventLoader


@pytest.fixture
def network_loader() -> NetworkLoader:
    return NetworkLoader(
        topology_parser=EurostagTopologyParser(
            ech_file=f"{TEST_DATA_FOLDER}/breaker_case/breaker_case.ech",
            dta_file=f"{TEST_DATA_FOLDER}/breaker_case/breaker_case.dta"
        ),
        load_flow_parser=EurostagLoadFlowParser(
            load_flow_results_file=f"{TEST_DATA_FOLDER}/breaker_case/breaker_case.lf"
        )
    )


@pytest.fixture
def simple_tfo() -> Transformer:
    return Transformer(
        resistance=Value(300, Unit.OHM, PUBase(100, Unit.OHM)),
        reactance=Value(1000, Unit.OHM, PUBase(100, Unit.OHM)),
        phase_shift_angle=Value(10, Unit.DEG),
        shunt_susceptance=Value(1, Unit.S, PUBase(100, Unit.S)),
        shunt_conductance=Value(1, Unit.S, PUBase(100, Unit.S)),
        transformer_type=8,
        initial_tap_number=3,
        ratio=1.09
    )


@pytest.fixture
def simple_load() -> Load:
    bus = Bus(
        name="BUS",
        base_voltage=Value(10, Unit.KV),
        voltage_magnitude=Value(12, Unit.KV, PUBase(10, unit=Unit.KV)),
        phase_angle=Value(0, Unit.DEG)
    )
    return Load(
        name="LOAD",
        bus=bus,
        active_power=Value(100, Unit.MW, PUBase(10, Unit.MW)),
        reactive_power=Value(30000, Unit.KVAR, PUBase(10, Unit.MVAR)),
        connected=True
    )


@pytest.fixture
def simple_capacitor_bank() -> CapacitorBank:
    bus = Bus(
        name="BUS",
        base_voltage=Value(10, Unit.KV),
        voltage_magnitude=Value(12, Unit.KV, PUBase(10, unit=Unit.KV)),
        phase_angle=Value(0, Unit.DEG)
    )
    return CapacitorBank(
        name="BANK",
        bus=bus,
        active_power=Value(0, Unit.MW, PUBase(10, Unit.MW)),
        reactive_power=Value(150, Unit.MVAR, PUBase(10, Unit.MVAR))
    )


@pytest.fixture
def simple_fictive_load() -> FictiveLoad:
    bus = Bus(
        name="BUS",
        base_voltage=Value(10, Unit.KV),
        voltage_magnitude=Value(12, Unit.KV, PUBase(10, unit=Unit.KV)),
        phase_angle=Value(0, Unit.DEG)
    )
    return FictiveLoad(
        name="FICTIVE_LOAD",
        bus=bus,
        admittance=3+2j,
        connected=True
    )


@pytest.fixture
def simple_line() -> Load:
    return Line(
        resistance=Value(300, Unit.OHM, PUBase(100, Unit.OHM)),
        reactance=Value(1000, Unit.OHM, PUBase(100, Unit.OHM)),
        shunt_conductance=Value(40, Unit.S, PUBase(10, Unit.S)),
        shunt_susceptance=Value(20, Unit.S, PUBase(10, Unit.S)),
    )


@pytest.fixture
def simple_generator() -> Generator:
    bus = Bus(
        name="BUS",
        base_voltage=Value(10, Unit.KV),
        voltage_magnitude=Value(12, Unit.KV, PUBase(10, unit=Unit.KV)),
        phase_angle=Value(0, Unit.DEG)
    )
    return Generator(
        name="GEN",
        type=GeneratorType.PV,
        bus=bus,
        direct_transient_reactance=Value(value=100, unit=Unit.OHM, base=PUBase(value=10, unit=Unit.OHM)),
        inertia_constant=Value(value=5, unit=Unit.MWS_PER_MVA),
        min_active_power=Value(value=0, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        active_power=Value(value=900, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        max_active_power=Value(value=1000, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        min_reactive_power=Value(value=100, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=300, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        max_reactive_power=Value(value=700, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        target_voltage_magnitude=Value(value=380, unit=Unit.KV, base=PUBase(value=10, unit=Unit.KV)),
        connected=True
    )


@pytest.fixture
def simple_dynamic_generator(simple_generator) -> DynamicGenerator:
    dynamic_generator = DynamicGenerator(simple_generator)
    dynamic_generator.add_rotor_angle(1, 4.5)
    dynamic_generator.add_rotor_angle(2, 8.1)
    dynamic_generator.add_angular_speed(1, -3.4)
    dynamic_generator.add_angular_speed(2, 4.1)
    dynamic_generator.add_network_state(1, NetworkState.DURING_FAULT)
    dynamic_generator.add_network_state(2, NetworkState.POST_FAULT)
    return dynamic_generator


@pytest.fixture
def simple_branch(simple_line, simple_tfo) -> Branch:
    branch = Branch(Bus("BUS1", Value(100, Unit.KV)), Bus("BUS2", Value(100, Unit.KV)))
    branch.parallel_elements = {
        "A": simple_line,
        "B": Line(
            resistance=Value(100, Unit.OHM, PUBase(100, Unit.OHM)),
            reactance=Value(2000, Unit.OHM, PUBase(100, Unit.OHM)),
            shunt_conductance=Value(10, Unit.S, PUBase(10, Unit.S)),
            shunt_susceptance=Value(30, Unit.S, PUBase(10, Unit.S)),
        ),
        "C": Line(
            resistance=Value(100, Unit.OHM, PUBase(100, Unit.OHM)),
            reactance=Value(2000, Unit.OHM, PUBase(100, Unit.OHM)),
            shunt_conductance=Value(10, Unit.S, PUBase(10, Unit.S)),
            shunt_susceptance=Value(30, Unit.S, PUBase(10, Unit.S)),
            closed_at_first_bus=False
        ),
        "D": simple_tfo
    }
    return branch


@pytest.fixture
def simple_bus() -> Bus:
    bus = Bus(
        name="BUS",
        base_voltage=Value(value=380, unit=Unit.KV),
        voltage_magnitude=Value(value=380, unit=Unit.KV, base=PUBase(value=10, unit=Unit.KV)),
        phase_angle=Value(value=20, unit=Unit.DEG)
    )
    bus.add_branch(Branch(bus, Bus("BUS3", Value(100, Unit.KV))))
    bus.add_generator(
        Generator(
            name="GEN",
            type=GeneratorType.PV,
            bus=bus,
            direct_transient_reactance=Value(value=100, unit=Unit.OHM, base=PUBase(value=10, unit=Unit.OHM)),
            inertia_constant=Value(value=5, unit=Unit.MWS_PER_MVA),
            min_active_power=Value(value=0, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
            active_power=Value(value=900, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
            max_active_power=Value(value=1000, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
            min_reactive_power=Value(value=100, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
            reactive_power=Value(value=300, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
            max_reactive_power=Value(value=600, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
            target_voltage_magnitude=Value(value=380, unit=Unit.KV, base=PUBase(value=10, unit=Unit.KV)),
            connected=True
        )
    )
    bus.add_load(
        Load(
            name="LOAD",
            bus=bus,
            active_power=Value(100, Unit.MW, PUBase(10, Unit.MW)),
            reactive_power=Value(30000, Unit.KVAR, PUBase(10, Unit.MVAR))
        )
    )
    bus.add_capacitor_bank(
        CapacitorBank(
            name="BANK",
            bus=bus,
            active_power=Value(0, Unit.MW, PUBase(10, Unit.MW)),
            reactive_power=Value(150, Unit.MVAR, PUBase(10, Unit.MVAR))
        )
    )
    return bus


@pytest.fixture
def simple_bus2() -> Bus:
    bus = Bus(
        name="BUS2",
        base_voltage=Value(value=380, unit=Unit.KV),
        voltage_magnitude=Value(value=380, unit=Unit.KV, base=PUBase(value=10, unit=Unit.KV)),
        phase_angle=Value(value=20, unit=Unit.DEG),
        type=BusType.SLACK
    )
    branch = Branch(Bus("BUS1", Value(100, Unit.KV)), bus)
    branch.parallel_elements = {
        "1": Line(
            resistance=Value(200, Unit.OHM, PUBase(100, Unit.OHM)),
            reactance=Value(3000, Unit.OHM, PUBase(100, Unit.OHM)),
            shunt_conductance=Value(20, Unit.S, PUBase(10, Unit.S)),
            shunt_susceptance=Value(30, Unit.S, PUBase(10, Unit.S)),
        )
    }
    bus.add_branch(branch)
    gen = Generator(
        name="GEN2",
        type=GeneratorType.PQ,
        bus=bus,
        direct_transient_reactance=Value(value=200, unit=Unit.OHM, base=PUBase(value=10, unit=Unit.OHM)),
        inertia_constant=Value(value=2, unit=Unit.MWS_PER_MVA),
        min_active_power=Value(value=100, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        active_power=Value(value=300, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        max_active_power=Value(value=900, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        min_reactive_power=Value(value=0, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        reactive_power=Value(value=100, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        max_reactive_power=Value(value=800, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        target_voltage_magnitude=Value(value=380, unit=Unit.KV, base=PUBase(value=10, unit=Unit.KV)),
        connected=True
    )
    bus.add_generator(gen)
    return bus


@pytest.fixture
def simple_parallel_breakers(simple_bus) -> ParallelBreakers:
    parallel_breakers = ParallelBreakers(
        first_bus=simple_bus,
        second_bus=Bus(
            name="BUS2",
            base_voltage=Value(value=380, unit=Unit.KV),
            voltage_magnitude=Value(value=380, unit=Unit.KV, base=PUBase(value=10, unit=Unit.KV)),
            phase_angle=Value(value=10, unit=Unit.DEG),
        )
    )
    parallel_breakers._breakers = {
        "1": Breaker(closed=True),
        "2": Breaker(closed=False)
    }
    return parallel_breakers


@pytest.fixture
def breaker_case_network() -> Network:
    # Buses
    buses = {
        "NGENA0": Bus(
            name="NGENA0",
            base_voltage=Value(value=24, unit=Unit.KV),
            voltage_magnitude=Value(value=0, unit=Unit.KV, base=PUBase(value=24, unit=Unit.KV)),
            phase_angle=Value(value=0, unit=Unit.DEG)
        ),
        "NGENA1": Bus(
            name="NGENA1",
            base_voltage=Value(value=24, unit=Unit.KV),
            voltage_magnitude=Value(value=24, unit=Unit.KV, base=PUBase(value=24, unit=Unit.KV)),
            phase_angle=Value(value=-15.17, unit=Unit.DEG)
        ),
        "NHVA1": Bus(
            name="NHVA1",
            base_voltage=Value(value=380, unit=Unit.KV),
            voltage_magnitude=Value(value=409.55, unit=Unit.KV, base=PUBase(value=380, unit=Unit.KV)),
            phase_angle=Value(value=-18.49, unit=Unit.DEG)
        ),
        "NGENB1": Bus(
            name="NGENB1",
            base_voltage=Value(value=24, unit=Unit.KV),
            voltage_magnitude=Value(value=23.65, unit=Unit.KV, base=PUBase(value=24, unit=Unit.KV)),
            phase_angle=Value(value=-6.56, unit=Unit.DEG)
        ),
        "NGENB2": Bus(
            name="NGENB2",
            base_voltage=Value(value=24, unit=Unit.KV),
            voltage_magnitude=Value(value=23.99, unit=Unit.KV, base=PUBase(value=24, unit=Unit.KV)),
            phase_angle=Value(value=-7.06, unit=Unit.DEG)
        ),
        "NHVA2": Bus(
            name="NHVA2",
            base_voltage=Value(value=380, unit=Unit.KV),
            voltage_magnitude=Value(value=406.94, unit=Unit.KV, base=PUBase(value=380, unit=Unit.KV)),
            phase_angle=Value(value=-2.21, unit=Unit.DEG)
        ),
        "NHVB1": Bus(
            name="NHVB1",
            base_voltage=Value(value=380, unit=Unit.KV),
            voltage_magnitude=Value(value=397.33, unit=Unit.KV, base=PUBase(value=380, unit=Unit.KV)),
            phase_angle=Value(value=-11.07, unit=Unit.DEG)
        ),
        "NHVD1": Bus(
            name="NHVD1",
            base_voltage=Value(value=380, unit=Unit.KV),
            voltage_magnitude=Value(value=399.81, unit=Unit.KV, base=PUBase(value=380, unit=Unit.KV)),
            phase_angle=Value(value=-11.06, unit=Unit.DEG)
        ),
        "NHVC1": Bus(
            name="NHVC1",
            base_voltage=Value(value=380, unit=Unit.KV),
            voltage_magnitude=Value(value=398.33, unit=Unit.KV, base=PUBase(value=380, unit=Unit.KV)),
            phase_angle=Value(value=-5.79, unit=Unit.DEG)
        ),
        "NHVC2": Bus(
            name="NHVC2",
            base_voltage=Value(value=380, unit=Unit.KV),
            voltage_magnitude=Value(value=395.63, unit=Unit.KV, base=PUBase(value=380, unit=Unit.KV)),
            phase_angle=Value(value=-8.07, unit=Unit.DEG)
        ),
        "NHVA3": Bus(
            name="NHVA3",
            base_voltage=Value(value=380, unit=Unit.KV),
            voltage_magnitude=Value(value=403.58, unit=Unit.KV, base=PUBase(value=380, unit=Unit.KV)),
            phase_angle=Value(value=-13.59, unit=Unit.DEG)
        ),
        "NHVCEQ": Bus(
            name="NHVCEQ",
            base_voltage=Value(value=100, unit=Unit.KV),
            voltage_magnitude=Value(value=106.54, unit=Unit.KV, base=PUBase(value=100, unit=Unit.KV)),
            phase_angle=Value(value=0, unit=Unit.DEG),
            type=BusType.SLACK
        ),
        "NHVD2": Bus(
            name="NHVD2",
            base_voltage=Value(value=380, unit=Unit.KV),
            voltage_magnitude=Value(value=399.81, unit=Unit.KV, base=PUBase(value=380, unit=Unit.KV)),
            phase_angle=Value(value=-11.06, unit=Unit.DEG)
        ),
        "NHVB2": Bus(
            name="NHVB2",
            base_voltage=Value(value=380, unit=Unit.KV),
            voltage_magnitude=Value(value=0, unit=Unit.KV, base=PUBase(value=380, unit=Unit.KV)),
            phase_angle=Value(value=0, unit=Unit.DEG)
        ),
        "NHVD3": Bus(
            name="NHVD3",
            base_voltage=Value(value=380, unit=Unit.KV),
            voltage_magnitude=Value(value=399.81, unit=Unit.KV, base=PUBase(value=380, unit=Unit.KV)),
            phase_angle=Value(value=-11.06, unit=Unit.DEG)
        )
    }

    # Generators
    gena0 = Generator(
        name="GENA0",
        type=GeneratorType.PV,
        bus=buses["NGENA0"],
        direct_transient_reactance=Value(
            value=0.422*(24**2/1150),
            unit=Unit.OHM,
            base=PUBase(value=24**2/100, unit=Unit.OHM)
        ),
        inertia_constant=Value(value=26.45, unit=Unit.MWS_PER_MVA),
        min_active_power=Value(value=-888888, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        active_power=Value(value=900, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        max_active_power=Value(value=888888, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        min_reactive_power=Value(value=-8888, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        reactive_power=Value(value=0, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        max_reactive_power=Value(value=8888, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        target_voltage_magnitude=Value(value=24, unit=Unit.KV, base=PUBase(value=24, unit=Unit.KV)),
        connected=False
    )
    buses["NGENA0"].add_generator(gena0)

    gena1 = Generator(
        name="GENA1",
        type=GeneratorType.PV,
        bus=buses["NGENA1"],
        direct_transient_reactance=Value(
            value=0.422*(24**2/1150),
            unit=Unit.OHM,
            base=PUBase(value=24**2/100, unit=Unit.OHM)
        ),
        inertia_constant=Value(value=72.45, unit=Unit.MWS_PER_MVA),
        min_active_power=Value(value=-999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        active_power=Value(value=900, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        max_active_power=Value(value=999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        min_reactive_power=Value(value=-9999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        reactive_power=Value(value=322.12, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        max_reactive_power=Value(value=9999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        target_voltage_magnitude=Value(value=24, unit=Unit.KV, base=PUBase(value=24, unit=Unit.KV)),
        connected=True
    )
    buses["NGENA1"].add_generator(gena1)

    genb1 = Generator(
        name="GENB1",
        type=GeneratorType.PQ,
        bus=buses["NGENB1"],
        direct_transient_reactance=Value(
            value=0.422*(24**2/444),
            unit=Unit.OHM,
            base=PUBase(value=24**2/100, unit=Unit.OHM)
        ),
        inertia_constant=Value(value=27.972, unit=Unit.MWS_PER_MVA),
        min_active_power=Value(value=-999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        active_power=Value(value=400, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        max_active_power=Value(value=999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        min_reactive_power=Value(value=-999999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        reactive_power=Value(value=190, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        max_reactive_power=Value(value=999999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        target_voltage_magnitude=None,
        connected=True
    )
    buses["NGENB1"].add_generator(genb1)

    genb2 = Generator(
        name="GENB2",
        type=GeneratorType.PQ,
        bus=buses["NGENB2"],
        direct_transient_reactance=Value(
            value=0.422*(24**2/111),
            unit=Unit.OHM,
            base=PUBase(value=24**2/100, unit=Unit.OHM)
        ),
        inertia_constant=Value(value=6.993, unit=Unit.MWS_PER_MVA),
        min_active_power=Value(value=-999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        active_power=Value(value=100, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        max_active_power=Value(value=999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        min_reactive_power=Value(value=-999999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        reactive_power=Value(value=45, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        max_reactive_power=Value(value=999999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        target_voltage_magnitude=None,
        connected=True
    )
    buses["NGENB2"].add_generator(genb2)

    gensl = Generator(
        name="NHVCEQ",
        type=GeneratorType.SLACK,
        bus=buses["NHVCEQ"],
        direct_transient_reactance=Value(
            value=0.422*(106.54**2/60000),
            unit=Unit.OHM,
            base=PUBase(value=100**2/100, unit=Unit.OHM)
        ),
        inertia_constant=Value(value=3780, unit=Unit.MWS_PER_MVA),
        min_active_power=Value(value=-999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        active_power=Value(value=2447.50, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        max_active_power=Value(value=999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        min_reactive_power=Value(value=-999999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        reactive_power=Value(value=221.88, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        max_reactive_power=Value(value=999999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        target_voltage_magnitude=Value(value=106.54, unit=Unit.KV, base=PUBase(value=100, unit=Unit.KV)),
        connected=True
    )
    buses["NHVCEQ"].add_generator(gensl)

    # Loads
    load1 = Load(
        name="LOAD",
        bus=buses["NHVA1"],
        active_power=Value(value=100, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=10, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        connected=True
    )
    buses["NHVA1"].add_load(load1)

    load2 = Load(
        name="NHVA1",
        bus=buses["NHVA1"],
        active_power=Value(value=900, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=90, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        connected=True
    )
    buses["NHVA1"].add_load(load2)

    load3 = Load(
        name="NHVB1",
        bus=buses["NHVB1"],
        active_power=Value(value=1000, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=300, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        connected=True
    )
    buses["NHVB1"].add_load(load3)

    load4 = Load(
        name="NHVC1",
        bus=buses["NHVC1"],
        active_power=Value(value=500, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=100, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        connected=True
    )
    buses["NHVC1"].add_load(load4)

    load5 = Load(
        name="NHVC2",
        bus=buses["NHVC2"],
        active_power=Value(value=600, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=200, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        connected=True
    )
    buses["NHVC2"].add_load(load5)

    load6 = Load(
        name="NHVCEQ",
        bus=buses["NHVCEQ"],
        active_power=Value(value=700, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=150, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        connected=True
    )
    buses["NHVCEQ"].add_load(load6)

    load7 = Load(
        name="GEN_GENA3",
        bus=buses["NGENA0"],
        active_power=Value(value=-300, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=0, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        connected=False
    )
    buses["NGENA0"].add_load(load7)

    load8 = Load(
        name="CONV_01",
        bus=buses["NHVD3"],
        active_power=Value(value=-290.4, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=310.51, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        connected=True
    )
    buses["NHVD3"].add_load(load8)

    # Capacitor banks
    bank1 = CapacitorBank(
        name="BANK1",
        bus=buses["NHVA1"],
        active_power=Value(value=0, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=10, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR))
    )
    buses["NHVA1"].add_capacitor_bank(bank1)

    bank2 = CapacitorBank(
        name="BANK2",
        bus=buses["NHVA1"],
        active_power=Value(value=10, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=20, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR))
    )
    buses["NHVA1"].add_capacitor_bank(bank2)

    bank3 = CapacitorBank(
        name="BANK3",
        bus=buses["NHVC1"],
        active_power=Value(value=0, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=20, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR))
    )
    buses["NHVC1"].add_capacitor_bank(bank3)

    bank4 = CapacitorBank(
        name="SVC 01",
        bus=buses["NHVC2"],
        active_power=Value(value=0, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=0.15, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR))
    )
    buses["NHVC2"].add_capacitor_bank(bank4)

    # Breakers
    parallel_breakers1 = ParallelBreakers(
        first_bus=buses["NHVD1"],
        second_bus=buses["NHVD2"]
    )
    parallel_breakers1["1"] = Breaker(closed=True)
    parallel_breakers1["2"] = Breaker(closed=False)

    parallel_breakers2 = ParallelBreakers(
        first_bus=buses["NHVD2"],
        second_bus=buses["NHVD3"]
    )
    parallel_breakers2["1"] = Breaker(closed=False)

    parallel_breakers3 = ParallelBreakers(
        first_bus=buses["NHVB1"],
        second_bus=buses["NHVB2"]
    )
    parallel_breakers3["1"] = Breaker(closed=False)

    # Line branches
    branch1 = Branch(buses["NHVA1"], buses["NHVA3"])
    branch1["1"] = Line(
        resistance=Value(value=0.00208*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.02285*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380**2/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.27869/(380**2/100),
            unit=Unit.S,
            base=PUBase(value=1/(380**2/100), unit=Unit.S)
        )
    )
    buses["NHVA1"].add_branch(branch1)
    buses["NHVA3"].add_branch(branch1)

    branch2 = Branch(buses["NHVA3"], buses["NHVD1"])
    branch2["1"] = Line(
        resistance=Value(value=0.00104*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.01142*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380**2/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.13934/(380**2/100),
            unit=Unit.S,
            base=PUBase(value=1/(380**2/100), unit=Unit.S)
        )
    )
    buses["NHVA3"].add_branch(branch2)
    buses["NHVD1"].add_branch(branch2)

    branch3 = Branch(buses["NHVC1"], buses["NHVA2"])
    branch3["1"] = Line(
        resistance=Value(value=0.00208*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.02285*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380**2/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.27869/(380**2/100),
            unit=Unit.S,
            base=PUBase(value=1/(380**2/100), unit=Unit.S)
        )
    )
    buses["NHVC1"].add_branch(branch3)
    buses["NHVA2"].add_branch(branch3)

    branch4 = Branch(buses["NHVC1"], buses["NHVC2"])
    branch4["1"] = Line(
        resistance=Value(value=0.00104*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.01142*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380**2/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.13934/(380**2/100),
            unit=Unit.S,
            base=PUBase(value=1/(380**2/100), unit=Unit.S)
        ),
        closed_at_first_bus=False,
        closed_at_second_bus=False
    )
    buses["NHVC1"].add_branch(branch4)
    buses["NHVC2"].add_branch(branch4)

    branch5 = Branch(buses["NHVD1"], buses["NHVC1"])
    branch5["1"] = Line(
        resistance=Value(value=0.00208*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.02285*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380**2/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.27869/(380**2/100),
            unit=Unit.S,
            base=PUBase(value=1/(380**2/100), unit=Unit.S)
        ),
        closed_at_first_bus=False
    )
    buses["NHVD1"].add_branch(branch5)
    buses["NHVC1"].add_branch(branch5)

    branch6 = Branch(buses["NHVC2"], buses["NHVB1"])
    branch6["1"] = Line(
        resistance=Value(value=0.00208*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.02285*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380**2/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.27869/(380**2/100),
            unit=Unit.S,
            base=PUBase(value=1/(380**2/100), unit=Unit.S)
        )
    )
    branch6["2"] = Line(
        resistance=Value(value=0.00208*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.02285*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380**2/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.27869/(380**2/100),
            unit=Unit.S,
            base=PUBase(value=1/(380**2/100), unit=Unit.S)
        )
    )
    buses["NHVC2"].add_branch(branch6)
    buses["NHVB1"].add_branch(branch6)

    branch7 = Branch(buses["NHVD1"], buses["NHVB1"])
    branch7["1"] = Line(
        resistance=Value(value=0.00104*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.01142*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380**2/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.13934/(380**2/100),
            unit=Unit.S,
            base=PUBase(value=1/(380**2/100), unit=Unit.S)
        )
    )
    branch7["2"] = Line(
        resistance=Value(value=0.00104*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.01142*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380**2/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.13934/(380**2/100),
            unit=Unit.S,
            base=PUBase(value=1/(380**2/100), unit=Unit.S)
        )
    )
    buses["NHVD1"].add_branch(branch7)
    buses["NHVB1"].add_branch(branch7)

    branch8 = Branch(buses["NHVC1"], buses["NHVCEQ"])
    branch8["1"] = Line(
        resistance=Value(value=0.002*(380*100/100), unit=Unit.OHM, base=PUBase(value=380*100/100, unit=Unit.OHM)),
        reactance=Value(value=0.011*(380*100/100), unit=Unit.OHM, base=PUBase(value=380*100/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380*100/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.27/(380*100/100),
            unit=Unit.S,
            base=PUBase(value=1/(380*100/100), unit=Unit.S)
        )
    )
    buses["NHVC1"].add_branch(branch8)
    buses["NHVCEQ"].add_branch(branch8)

    branch9 = Branch(buses["NHVC2"], buses["NHVCEQ"])
    branch9["1"] = Line(
        resistance=Value(value=0.002*(380*100/100), unit=Unit.OHM, base=PUBase(value=380*100/100, unit=Unit.OHM)),
        reactance=Value(value=0.022*(380*100/100), unit=Unit.OHM, base=PUBase(value=380*100/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380*100/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.27/(380*100/100),
            unit=Unit.S,
            base=PUBase(value=1/(380*100/100), unit=Unit.S)
        )
    )
    buses["NHVC2"].add_branch(branch9)
    buses["NHVCEQ"].add_branch(branch9)

    branch10 = Branch(buses["NHVD2"], buses["NHVB1"])
    branch10["1"] = Line(
        resistance=Value(value=0.00104*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.01142*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380**2/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.13934/(380**2/100),
            unit=Unit.S,
            base=PUBase(value=1/(380**2/100), unit=Unit.S)
        )
    )
    buses["NHVD2"].add_branch(branch10)
    buses["NHVB1"].add_branch(branch10)

    branch11 = Branch(buses["NHVD3"], buses["NHVC1"])
    branch11["1"] = Line(
        resistance=Value(value=0.00104*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.01142*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380**2/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.13934/(380**2/100),
            unit=Unit.S,
            base=PUBase(value=1/(380**2/100), unit=Unit.S)
        )
    )
    buses["NHVD3"].add_branch(branch11)
    buses["NHVC1"].add_branch(branch11)

    # Transformer branches
    branch12 = Branch(buses["NGENA1"], buses["NHVA1"])
    branch12["1"] = Transformer(
        resistance=Value(value=0.000185*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.00769*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=1, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        shunt_susceptance=Value(value=1, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        phase_shift_angle=Value(value=18, unit=Unit.DEG),
        transformer_type=8,
        ratio=1.09
    )
    branch12["2"] = Transformer(
        resistance=Value(value=0.000185*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.00769*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=1, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        shunt_susceptance=Value(value=1, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        transformer_type=8,
        ratio=1.09
    )
    buses["NGENA1"].add_branch(branch12)
    buses["NHVA1"].add_branch(branch12)

    branch13 = Branch(buses["NGENB1"], buses["NHVB1"])
    branch13["1"] = Transformer(
        resistance=Value(value=0.000541*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.02251*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=1, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        shunt_susceptance=Value(value=1, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        phase_shift_angle=Value(value=18, unit=Unit.DEG),
        transformer_type=8,
        ratio=1.09
    )
    buses["NGENB1"].add_branch(branch13)
    buses["NHVB1"].add_branch(branch13)

    branch14 = Branch(buses["NGENB2"], buses["NHVB1"])
    branch14["1"] = Transformer(
        resistance=Value(value=0.02164*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.09006*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=1, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        shunt_susceptance=Value(value=1, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        phase_shift_angle=Value(value=18, unit=Unit.DEG),
        transformer_type=8,
        ratio=1.09
    )
    buses["NGENB2"].add_branch(branch14)
    buses["NHVB1"].add_branch(branch14)

    branch15 = Branch(buses["NGENA0"], buses["NHVA1"])
    branch15["1"] = Transformer(
        resistance=Value(value=0.02164*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.09006*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        closed_at_second_bus=False,
        shunt_conductance=Value(value=1, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        shunt_susceptance=Value(value=1, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        phase_shift_angle=Value(value=18, unit=Unit.DEG),
        transformer_type=8,
        ratio=1.09
    )
    buses["NGENA0"].add_branch(branch15)
    buses["NHVA1"].add_branch(branch15)

    branch16 = Branch(buses["NHVA1"], buses["NHVA2"])
    resistance = 0.21 / 100 * (400**2 / 1000)
    impedance = 10 / 100 * (400**2 / 1000)
    branch16["1"] = Transformer(
        resistance=Value(value=resistance, unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(
            value=math.sqrt(impedance**2 - resistance**2),
            unit=Unit.OHM,
            base=PUBase(value=380**2/100, unit=Unit.OHM)
        ),
        initial_tap_number=0,
        phase_shift_angle=Value(value=18, unit=Unit.DEG),
        shunt_conductance=Value(value=1, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        shunt_susceptance=Value(value=1, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        transformer_type=8,
        ratio=1.09
    )
    buses["NHVA1"].add_branch(branch16)
    buses["NHVA2"].add_branch(branch16)

    return Network(
        buses=list(buses.values()),
        breakers=[parallel_breakers1, parallel_breakers2, parallel_breakers3],
        base_power=Value(100, Unit.MVA)
    )


@pytest.fixture
def simple_network() -> Network:
    # Buses
    buses = {
        "GENBUS": Bus(
            name="GENBUS",
            base_voltage=Value(value=24, unit=Unit.KV),
            voltage_magnitude=Value(value=24, unit=Unit.KV, base=PUBase(value=24, unit=Unit.KV)),
            phase_angle=Value(value=-15.17, unit=Unit.DEG)
        ),
        "SLACKBUS": Bus(
            name="SLACKBUS",
            base_voltage=Value(value=100, unit=Unit.KV),
            voltage_magnitude=Value(value=105, unit=Unit.KV, base=PUBase(value=100, unit=Unit.KV)),
            phase_angle=Value(value=0, unit=Unit.DEG),
            type=BusType.SLACK
        ),
        "BUS1": Bus(
            name="BUS1",
            base_voltage=Value(value=380, unit=Unit.KV),
            voltage_magnitude=Value(value=400, unit=Unit.KV, base=PUBase(value=380, unit=Unit.KV)),
            phase_angle=Value(value=-2.21, unit=Unit.DEG)
        ),
        "BUS2": Bus(
            name="BUS2",
            base_voltage=Value(value=380, unit=Unit.KV),
            voltage_magnitude=Value(value=400, unit=Unit.KV, base=PUBase(value=380, unit=Unit.KV)),
            phase_angle=Value(value=-2.21, unit=Unit.DEG)
        ),
        "BUS3": Bus(
            name="BUS3",
            base_voltage=Value(value=380, unit=Unit.KV),
            voltage_magnitude=Value(value=398, unit=Unit.KV, base=PUBase(value=380, unit=Unit.KV)),
            phase_angle=Value(value=-2.31, unit=Unit.DEG)
        )
    }

    # Generators
    gen1 = Generator(
        name="GEN1",
        type=GeneratorType.PV,
        bus=buses["GENBUS"],
        direct_transient_reactance=Value(
            value=0.576*(24**2/100),
            unit=Unit.OHM,
            base=PUBase(value=24**2/100, unit=Unit.OHM)
        ),
        inertia_constant=Value(value=6.3, unit=Unit.MWS_PER_MVA),
        min_active_power=Value(value=-999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        active_power=Value(value=900, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        max_active_power=Value(value=999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        min_reactive_power=Value(value=-9999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        reactive_power=Value(value=300, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        max_reactive_power=Value(value=9999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        target_voltage_magnitude=Value(value=24, unit=Unit.KV, base=PUBase(value=24, unit=Unit.KV)),
        connected=True
    )
    buses["GENBUS"].add_generator(gen1)

    gen2 = Generator(
        name="GEN2",
        type=GeneratorType.PQ,
        bus=buses["GENBUS"],
        direct_transient_reactance=Value(
            value=0.576*(24**2/100),
            unit=Unit.OHM,
            base=PUBase(value=24**2/100, unit=Unit.OHM)
        ),
        inertia_constant=Value(value=6.3, unit=Unit.MWS_PER_MVA),
        min_active_power=Value(value=-999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        active_power=Value(value=400, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        max_active_power=Value(value=999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        min_reactive_power=Value(value=-9999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        reactive_power=Value(value=200, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        max_reactive_power=Value(value=9999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        target_voltage_magnitude=None,
        connected=True
    )
    buses["GENBUS"].add_generator(gen2)

    gen3 = Generator(
        name="GEN3",
        type=GeneratorType.PQ,
        bus=buses["GENBUS"],
        direct_transient_reactance=Value(
            value=0.576*(24**2/100),
            unit=Unit.OHM,
            base=PUBase(value=24**2/100, unit=Unit.OHM)
        ),
        inertia_constant=Value(value=6.3, unit=Unit.MWS_PER_MVA),
        min_active_power=Value(value=-999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        active_power=Value(value=600, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        max_active_power=Value(value=999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        min_reactive_power=Value(value=-999999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        reactive_power=Value(value=700, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        max_reactive_power=Value(value=999999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        target_voltage_magnitude=None,
        connected=False
    )
    buses["GENBUS"].add_generator(gen3)

    slackgen = Generator(
        name="SLACKGEN",
        type=GeneratorType.SLACK,
        bus=buses["SLACKBUS"],
        direct_transient_reactance=Value(
            value=0.400*(100**2/100),
            unit=Unit.OHM,
            base=PUBase(value=100**2/100, unit=Unit.OHM)
        ),
        inertia_constant=Value(value=6.3, unit=Unit.MWS_PER_MVA),
        min_active_power=Value(value=-999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        active_power=Value(value=200, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        max_active_power=Value(value=999999, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        min_reactive_power=Value(value=-999999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        reactive_power=Value(value=200, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        max_reactive_power=Value(value=999999, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        target_voltage_magnitude=Value(value=105, unit=Unit.KV, base=PUBase(value=100, unit=Unit.KV)),
        connected=True
    )
    buses["SLACKBUS"].add_generator(slackgen)

    # Loads
    load1 = Load(
        name="LOAD1",
        bus=buses["BUS3"],
        active_power=Value(value=100, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=10, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        connected=True
    )
    buses["BUS3"].add_load(load1)

    load2 = Load(
        name="LOAD2",
        bus=buses["BUS2"],
        active_power=Value(value=900, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=90, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        connected=True
    )
    buses["BUS2"].add_load(load2)

    load3 = Load(
        name="LOAD3",
        bus=buses["BUS1"],
        active_power=Value(value=800, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=70, unit=Unit.MVAR, base=PUBase(value=100, unit=Unit.MVAR)),
        connected=False
    )
    buses["BUS1"].add_load(load3)

    # Capacitor banks
    bank = CapacitorBank(
        name="BANK",
        bus=buses["BUS2"],
        active_power=Value(value=0, unit=Unit.MW, base=PUBase(value=100, unit=Unit.MW)),
        reactive_power=Value(value=150, unit=Unit.MVAR, base=PUBase(value=10, unit=Unit.MVAR))
    )
    buses["BUS2"].add_capacitor_bank(bank)

    # Breakers
    parallel_breakers = ParallelBreakers(
        first_bus=buses["BUS1"],
        second_bus=buses["BUS2"]
    )
    parallel_breakers["1"] = Breaker(closed=True)

    # Line branches
    branch1 = Branch(buses["BUS2"], buses["BUS3"])
    branch1["1"] = Line(
        resistance=Value(value=0.002*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.01*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380**2/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.3/(380**2/100),
            unit=Unit.S,
            base=PUBase(value=1/(380**2/100), unit=Unit.S)
        ),
    )
    branch1["2"] = Line(
        resistance=Value(value=0.002*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.01*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380**2/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.3/(380**2/100),
            unit=Unit.S,
            base=PUBase(value=1/(380**2/100), unit=Unit.S)
        ),
    )
    branch1["3"] = Line(
        resistance=Value(value=0.002*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.01*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1/(380**2/100), unit=Unit.S)),
        shunt_susceptance=Value(
            value=2*0.3/(380**2/100),
            unit=Unit.S,
            base=PUBase(value=1/(380**2/100), unit=Unit.S)
        ),
        closed_at_second_bus=False
    )
    buses["BUS2"].add_branch(branch1)
    buses["BUS3"].add_branch(branch1)

    # Transformer branches
    branch2 = Branch(buses["GENBUS"], buses["BUS3"])
    branch2["1"] = Transformer(
        resistance=Value(value=0.0001*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.007*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        shunt_susceptance=Value(value=0, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        phase_shift_angle=Value(value=0, unit=Unit.DEG),
        transformer_type=8,
        ratio=1.
    )
    buses["GENBUS"].add_branch(branch2)
    buses["BUS3"].add_branch(branch2)

    branch3 = Branch(buses["SLACKBUS"], buses["BUS1"])
    branch3["1"] = Transformer(
        resistance=Value(value=0.0005*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        reactance=Value(value=0.02*(380**2/100), unit=Unit.OHM, base=PUBase(value=380**2/100, unit=Unit.OHM)),
        shunt_conductance=Value(value=0, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        shunt_susceptance=Value(value=0, unit=Unit.S, base=PUBase(value=1, unit=Unit.S)),
        phase_shift_angle=Value(value=0, unit=Unit.DEG),
        transformer_type=8,
        ratio=1.
    )
    buses["SLACKBUS"].add_branch(branch3)
    buses["BUS1"].add_branch(branch3)

    return Network(
        buses=list(buses.values()),
        breakers=[parallel_breakers],
        base_power=Value(100, Unit.MVA)
    )


@pytest.fixture
def simple_network_admittance_matrix(simple_network) -> BusMatrix:
    # Bus voltages
    v_bus3 = cmath.rect(1.0473684210526315, np.deg2rad(-2.31))
    v_bus1_bus2 = cmath.rect(1.0526315789473684, np.deg2rad(-2.21))

    # Generator admittances
    y_gen1 = 1 / 0.576j
    y_gen2 = y_gen1
    y_slackgen = 1 / 0.400j

    # Load admittances
    y_ld1 = (1 - 0.1j) / (abs(v_bus3) ** 2)
    y_ld2 = (9 - 0.9j) / (abs(v_bus1_bus2) ** 2)

    # Capacitor bank admittances
    y_bk = (-15j) / (abs(v_bus1_bus2) ** 2)

    # Branch admittances
    y_genbus_bus3 = 1 / (0.0001 + 0.007j)
    y_slackbus_bus1 = 1 / (0.0005 + 0.02j)
    y_bus2_bus3 = 2 * (1 / (0.002 + 0.01j))

    # Branch shunt admittances (take into account round of numbers to 5 decimals)
    ys_bus2_bus3 = 2 * (0 + 0.6j)

    # Build sorted indexes
    buses = simple_network.get_simplified_network()[0].buses
    bus_indexes = {
        buses[6].name: 0,
        buses[5].name: 1,
        buses[4].name: 2,
        buses[2].name: 3,
        buses[1].name: 4,
        buses[3].name: 5,
        buses[0].name: 6
    }
    return BusMatrix(
        np.array(
            [
                [y_slackgen, 0, 0, 0, -y_slackgen, 0, 0],
                [0, y_gen2, 0, 0, 0, 0, -y_gen2],
                [0, 0, y_gen1, 0, 0, 0, -y_gen1],
                [0, 0, 0, y_ld2 + y_bk + y_bus2_bus3 + y_slackbus_bus1 + ys_bus2_bus3 / 2, -y_slackbus_bus1,
                 -y_bus2_bus3, 0],
                [-y_slackgen, 0, 0, -y_slackbus_bus1, y_slackgen + y_slackbus_bus1, 0, 0],
                [0, 0, 0, -y_bus2_bus3, 0, y_ld1 + y_genbus_bus3 + y_bus2_bus3 + ys_bus2_bus3 / 2, -y_genbus_bus3],
                [0, -y_gen1, -y_gen2, 0, 0, -y_genbus_bus3, y_gen1 + y_gen2 + y_genbus_bus3]
            ]
        ),
        bus_indexes
    )


@pytest.fixture
def simple_network_impedance_matrix(simple_network_admittance_matrix) -> BusMatrix:
    matrix = simple_network_admittance_matrix._matrix
    reversed_matrix = np.linalg.inv(matrix)
    return BusMatrix(
        matrix=reversed_matrix,
        bus_indexes=simple_network_admittance_matrix._bus_indexes
    )


@pytest.fixture
def simple_network_reduced_admittance_matrix(simple_network) -> BusMatrix:
    buses = simple_network.get_simplified_network()[0].buses
    return BusMatrix(
        matrix=np.array(
            [
                [0.11814481-2.13693591j, 0.08127585+0.17088014j, 0.08127585+0.17088014j],
                [0.08127585+0.17088014j, 0.06041539-1.58170402j, 0.06041539+0.15440709j],
                [0.08127585+0.17088014j, 0.06041539+0.15440709j, 0.06041539-1.58170402j]
            ]
        ),
        bus_indexes={buses[6].name: 0, buses[5].name: 1, buses[4].name: 2}
    )


@pytest.fixture
def generator_cluster(breaker_case_network) -> GeneratorCluster:
    generators = breaker_case_network.get_simplified_network()[0].generators
    dynamic_generators = set()
    for i, generator in enumerate(generators):
        dynamic_generator = DynamicGenerator(generator)
        dynamic_generator.add_rotor_angle(time=2, rotor_angle=i)
        dynamic_generator.add_network_state(time=2, state=NetworkState.DURING_FAULT)
        dynamic_generators.add(dynamic_generator)
    return GeneratorCluster(dynamic_generators)


@pytest.fixture
def case1_line_fault_event_loader() -> EventLoader:
    return EventLoader(
        event_parser=EurostagEventParser(
            eurostag_event_file=f"{TEST_DATA_FOLDER}/case1/case1_line.seq"
        )
    )


@pytest.fixture
def case1_bus_fault_event_loader() -> EventLoader:
    return EventLoader(
        event_parser=EurostagEventParser(
            eurostag_event_file=f"{TEST_DATA_FOLDER}/case1/case1_bus.seq"
        )
    )


@pytest.fixture
def case1_network_line_fault(case1_line_fault_event_loader) -> Network:
    network = NetworkLoader(
        topology_parser=EurostagTopologyParser(
            ech_file=f"{TEST_DATA_FOLDER}/case1/case1.ech",
            dta_file=f"{TEST_DATA_FOLDER}/case1/case1.dta"
        ),
        load_flow_parser=EurostagLoadFlowParser(
            load_flow_results_file=f"{TEST_DATA_FOLDER}/case1/case1.lf"
        )
    ).load_network()
    failure_events, mitigation_events = case1_line_fault_event_loader.load_events()
    network.initialize_simplified_network()
    network.provide_events(failure_events, mitigation_events)
    return network


@pytest.fixture
def case1_line_fault_dynamic_generators(case1_network_line_fault) -> Set[DynamicGenerator]:
    generators = {
        DynamicGenerator(gen) for gen in case1_network_line_fault.get_state(NetworkState.POST_FAULT).generators
    }
    return generators


@pytest.fixture
def case1_line_fault_dynamic_generators_updated(
    case1_line_fault_zoomib_eac, case1_line_fault_omib_taylor_series, case1_network_line_fault
) -> Set[DynamicGenerator]:
    generators = {
        DynamicGenerator(gen) for gen in case1_network_line_fault.get_state(NetworkState.POST_FAULT).generators
    }

    # Results with SEEAC and ZOOMIB
    critical_angle = case1_line_fault_zoomib_eac.critical_clearing_angle
    maximum_angle = case1_line_fault_zoomib_eac.maximum_angle
    angles = [critical_angle, maximum_angle]
    critical_time, maximum_time = case1_line_fault_omib_taylor_series.get_trajectory_times(angles, critical_angle)
    series = GeneratorTaylorSeries(case1_network_line_fault)
    series.update_generator_angles(generators, critical_time, maximum_time, 5, 5)
    return generators


@pytest.fixture
def case1_network() -> Network:
    return NetworkLoader(
        topology_parser=EurostagTopologyParser(
            ech_file=f"{TEST_DATA_FOLDER}/case1/case1.ech",
            dta_file=f"{TEST_DATA_FOLDER}/case1/case1.dta"
        ),
        load_flow_parser=EurostagLoadFlowParser(
            load_flow_results_file=f"{TEST_DATA_FOLDER}/case1/case1.lf"
        )
    ).load_network()


@pytest.fixture
def acc_cc_identifier(
    case1_network_line_fault, case1_line_fault_dynamic_generators
) -> AccelerationCriticalClustersIdentifier:
    return AccelerationCriticalClustersIdentifier(case1_network_line_fault, case1_line_fault_dynamic_generators)


@pytest.fixture
def acc_cc_identifier_domib(
    case1_network_line_fault, case1_line_fault_dynamic_generators_updated
) -> AccelerationCriticalClustersIdentifier:
    return AccelerationCriticalClustersIdentifier(case1_network_line_fault, case1_line_fault_dynamic_generators_updated)


@pytest.fixture
def comp_cc_identifier(
    case1_network_line_fault, case1_line_fault_dynamic_generators
) -> CompositeCriticalClustersIdentifier:
    return CompositeCriticalClustersIdentifier(case1_network_line_fault, case1_line_fault_dynamic_generators)


@pytest.fixture
def trajectory_cc_identifier(
    case1_network_line_fault, case1_line_fault_dynamic_generators_updated
) -> TrajectoryCriticalClustersIdentifier:
    return TrajectoryCriticalClustersIdentifier(
        network=case1_network_line_fault,
        generators=case1_line_fault_dynamic_generators_updated
    )


@pytest.fixture
def during_fault_cc_identifier(
    case1_network_line_fault, case1_line_fault_dynamic_generators_updated
) -> DuringFaultTrajectoryCriticalClustersIdentifier:
    return DuringFaultTrajectoryCriticalClustersIdentifier(
        network=case1_network_line_fault,
        generators=case1_line_fault_dynamic_generators_updated,
        during_fault_identification_time_step=175
    )


@pytest.fixture
def case1_zoomib(case1_network_line_fault, acc_cc_identifier) -> ZOOMIB:
    critical_cluster, non_critical_cluster = next(acc_cc_identifier.candidate_clusters)
    return ZOOMIB(case1_network_line_fault, critical_cluster, non_critical_cluster)


@pytest.fixture
def case1_revised_zoomib(case1_network_line_fault, acc_cc_identifier) -> RevisedZOOMIB:
    critical_cluster, non_critical_cluster = next(acc_cc_identifier.candidate_clusters)
    return RevisedZOOMIB(case1_network_line_fault, critical_cluster, non_critical_cluster)


@pytest.fixture
def case1_coomib(case1_network_line_fault, acc_cc_identifier) -> COOMIB:
    critical_cluster, non_critical_cluster = next(acc_cc_identifier.candidate_clusters)
    return COOMIB(case1_network_line_fault, critical_cluster, non_critical_cluster)


@pytest.fixture
def case1_revised_coomib(case1_network_line_fault, acc_cc_identifier) -> RevisedCOOMIB:
    critical_cluster, non_critical_cluster = next(acc_cc_identifier.candidate_clusters)
    return RevisedCOOMIB(case1_network_line_fault, critical_cluster, non_critical_cluster)


@pytest.fixture
def case1_domib(case1_network_line_fault, acc_cc_identifier_domib) -> DOMIB:
    critical_cluster, non_critical_cluster = next(acc_cc_identifier_domib.candidate_clusters)
    return DOMIB(case1_network_line_fault, critical_cluster, non_critical_cluster)


@pytest.fixture
def case1_revised_domib(case1_network_line_fault, acc_cc_identifier_domib) -> RevisedDOMIB:
    critical_cluster, non_critical_cluster = next(acc_cc_identifier_domib.candidate_clusters)
    revised_domib = RevisedDOMIB(case1_network_line_fault, critical_cluster, non_critical_cluster)
    return revised_domib


@pytest.fixture
def breaker_event_dto() -> event_dtos.BreakerEvent:
    return event_dtos.BreakerEvent(
        time=10.3,
        first_bus_name="BUS1",
        second_bus_name="BUS2",
        parallel_id="1",
        breaker_closed=False
    )


@pytest.fixture
def branch_event_dto() -> event_dtos.BranchEvent:
    return event_dtos.BranchEvent(
        time=10.3,
        first_bus_name="BUS1",
        second_bus_name="BUS2",
        parallel_id="1",
        breaker_position=event_dtos.BreakerPosition.FIRST_BUS,
        breaker_closed=True
    )


@pytest.fixture
def bus_short_circuit_event_dto() -> event_dtos.BusShortCircuitEvent:
    return event_dtos.BusShortCircuitEvent(
        time=10.3,
        bus_name="BUS1",
        fault_resistance=ValueDto(value=3, unit=UnitDto.OHM),
        fault_reactance=ValueDto(value=0, unit=UnitDto.OHM)
    )


@pytest.fixture
def bus_short_circuit_clearing_event_dto() -> event_dtos.BusShortCircuitClearingEvent:
    return event_dtos.BusShortCircuitClearingEvent(
        time=10.3,
        bus_name="BUS1"
    )


@pytest.fixture
def line_short_circuit_event_dto() -> event_dtos.LineShortCircuitEvent:
    return event_dtos.LineShortCircuitEvent(
        time=10.3,
        first_bus_name="BUS1",
        second_bus_name="BUS2",
        parallel_id="1",
        fault_position=0.01,
        fault_resistance=ValueDto(value=3, unit=UnitDto.OHM),
        fault_reactance=ValueDto(value=0, unit=UnitDto.OHM)
    )


@pytest.fixture
def line_short_circuit_clearing_event_dto() -> event_dtos.LineShortCircuitClearingEvent:
    return event_dtos.LineShortCircuitClearingEvent(
        time=10.3,
        first_bus_name="BUS1",
        second_bus_name="BUS2",
        parallel_id="4"
    )


@pytest.fixture
def case1_line_fault_zoomib_eac(case1_network_line_fault) -> EAC:
    generators = {
        DynamicGenerator(gen) for gen in case1_network_line_fault.get_state(NetworkState.POST_FAULT).generators
    }
    identifier = AccelerationCriticalClustersIdentifier(case1_network_line_fault, generators)
    critical_cluster, non_critical_cluster = next(identifier.candidate_clusters)
    omib = ZOOMIB(case1_network_line_fault, critical_cluster, non_critical_cluster)
    return EAC(omib, np.pi / 100)


@pytest.fixture
def case1_line_fault_omib_taylor_series(case1_line_fault_zoomib_eac) -> OMIBTaylorSeries:
    return OMIBTaylorSeries(case1_line_fault_zoomib_eac.omib)


@pytest.fixture
def case1_line_fault_omib_numerical_integrator(case1_line_fault_zoomib_eac) -> OMIBNumericalIntegrator:
    return OMIBNumericalIntegrator(case1_line_fault_zoomib_eac.omib)


@pytest.fixture
def case1_line_fault_domib_eac(case1_network_line_fault, case1_line_fault_zoomib_eac) -> EAC:
    # Get critical and maximum times with static EAC
    omib_series = OMIBTaylorSeries(case1_line_fault_zoomib_eac.omib)
    angles = [case1_line_fault_zoomib_eac.critical_clearing_angle, case1_line_fault_zoomib_eac.maximum_angle]
    cc_time, max_time = omib_series.get_trajectory_times(angles, case1_line_fault_zoomib_eac.critical_clearing_angle)

    # Update generator angles
    generators = {
        DynamicGenerator(gen) for gen in case1_network_line_fault.get_state(NetworkState.POST_FAULT).generators
    }
    generator_series = GeneratorTaylorSeries(case1_network_line_fault)
    generator_series.update_generator_angles(generators, cc_time, max_time, 5, 5)

    # Get critical clusters and create OMIB
    identifier = AccelerationCriticalClustersIdentifier(case1_network_line_fault, generators)
    critical_cluster, non_critical_cluster = next(identifier.candidate_clusters)
    omib = DOMIB(case1_network_line_fault, critical_cluster, non_critical_cluster)

    return EAC(omib, np.pi / 100)


@pytest.fixture
def basic_domib_eeac_tree() -> EEACTree:
    tree_parser = JSONTreeParser(f"{TEST_DATA_FOLDER}/eeac_trees/basic_domib_tree.json")
    return EEACTreeLoader(tree_parser).load_eeac_tree()


@pytest.fixture
def case1_ccs_identifier_tree_node_no_inputs(basic_domib_eeac_tree) -> CriticalClustersIdentifierNode:
    return basic_domib_eeac_tree[0]


@pytest.fixture
def case1_ccs_identifier_tree_node(
    basic_domib_eeac_tree, case1_line_fault_dynamic_generators, case1_network_line_fault
) -> CriticalClustersIdentifierNode:
    node = basic_domib_eeac_tree[0]
    # Provide inputs
    node.inputs = CriticalClustersIdentifierNodeInputs(
        network=case1_network_line_fault,
        dynamic_generators=case1_line_fault_dynamic_generators
    )
    return node


@pytest.fixture
def case1_ccs_evaluator_tree_node(
    basic_domib_eeac_tree, case1_line_fault_zoomib_eac, case1_network_line_fault
) -> CriticalClustersEvaluatorNode:
    node = basic_domib_eeac_tree[1]
    # Provide inputs
    node.inputs = CriticalClustersEvaluatorNodeInputs(
        network=case1_network_line_fault,
        clusters_iterator=iter([
            (
                case1_line_fault_zoomib_eac.omib.critical_cluster,
                case1_line_fault_zoomib_eac.omib.non_critical_cluster
            )
        ])
    )
    return node


@pytest.fixture
def case1_cc_selector_tree_node(basic_domib_eeac_tree, case1_zoomib) -> CriticalClusterSelectorNode:
    node = basic_domib_eeac_tree[2]
    # Provide inputs
    inputs = [
        EEACClusterResults(
            critical_angle=1,
            critical_time=0.1,
            maximum_angle=2,
            maximum_time=1.4,
            critical_cluster=case1_zoomib.critical_cluster,
            non_critical_cluster=case1_zoomib.non_critical_cluster,
            dynamic_generators=case1_zoomib.critical_cluster.generators.union(
                case1_zoomib.non_critical_cluster.generators
            ),
            omib_stability_state=OMIBStabilityState.POTENTIALLY_STABLE,
            omib_swing_state=OMIBSwingState.FORWARD
        ),
        EEACClusterResults(
            critical_angle=0.5,
            critical_time=0.01,
            maximum_angle=4,
            maximum_time=3.4,
            critical_cluster=case1_zoomib.critical_cluster,
            non_critical_cluster=case1_zoomib.non_critical_cluster,
            dynamic_generators=case1_zoomib.critical_cluster.generators.union(
                case1_zoomib.non_critical_cluster.generators
            ),
            omib_stability_state=OMIBStabilityState.POTENTIALLY_STABLE,
            omib_swing_state=OMIBSwingState.FORWARD
        )
    ]
    node.inputs = CriticalClusterSelectorNodeInputs(cluster_results_iterator=iter(inputs))
    return node


@pytest.fixture
def case1_generator_traj_calc_tree_node(
    basic_domib_eeac_tree, case1_zoomib, case1_network_line_fault
) -> GeneratorTrajectoryCalculatorNode:
    node = basic_domib_eeac_tree[3]
    results = EEACClusterResults(
        critical_angle=0.5,
        critical_time=0.01,
        maximum_angle=4,
        maximum_time=3.4,
        critical_cluster=case1_zoomib.critical_cluster,
        non_critical_cluster=case1_zoomib.non_critical_cluster,
        dynamic_generators=case1_zoomib.critical_cluster.generators.union(
            case1_zoomib.non_critical_cluster.generators
        ),
        omib_stability_state=OMIBStabilityState.POTENTIALLY_STABLE,
        omib_swing_state=OMIBSwingState.FORWARD
    )
    # Provide inputs
    node.inputs = GeneratorTrajectoryCalculatorNodeInputs(
        network=case1_network_line_fault,
        cluster_results=results
    )
    return node


@pytest.fixture
def case1_omib_tree_node(basic_domib_eeac_tree, case1_zoomib, case1_network_line_fault) -> OMIBNode:
    node = basic_domib_eeac_tree[4]
    # Provide inputs
    node.inputs = OMIBNodeInputs(
        network=case1_network_line_fault,
        critical_cluster=case1_zoomib.critical_cluster,
        non_critical_cluster=case1_zoomib.non_critical_cluster
    )
    return node


@pytest.fixture
def case1_eac_tree_node(basic_domib_eeac_tree, case1_zoomib) -> EACNode:
    node = basic_domib_eeac_tree[5]
    node.inputs = EACNodeInputs(omib=case1_zoomib)
    return node


@pytest.fixture
def case1_omib_traj_calc_tree_node(basic_domib_eeac_tree, case1_zoomib) -> OMIBTrajectoryCalculatorNode:
    node = basic_domib_eeac_tree[6]
    case1_zoomib.stability_state = OMIBStabilityState.POTENTIALLY_STABLE
    node.inputs = OMIBTrajectoryCalculatorNodeInputs(
        critical_angle=1.2,
        maximum_angle=6.3,
        omib=case1_zoomib
    )
    return node


@pytest.fixture
def simple_ccs_identifier_node_data() -> tree_dtos.EEACTreeNode:
    config = tree_dtos.CriticalClustersIdentifierConfiguration(
        identifier_type=tree_dtos.CriticalClustersIdentifierType.ACCELERATION,
        threshold=0.7,
        max_number_candidates=1
    )
    return tree_dtos.EEACTreeNode(
        id=1,
        name="CCs Identifier",
        type=tree_dtos.EEACTreeNodeType.CRITICAL_CLUSTERS_IDENTIFIER,
        configuration=config
    )
