"""
Module for enums.

:module: enums
"""
# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.
from __future__ import annotations

from enum import Enum


class BusType(Enum):
    """
    Bustype.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar PQ: PQ.
    :cvar PV: PV.
    :cvar SLACK: SLACK.
    :cvar GEN_INT_VOLT: GEN INT VOLT.
    """
    PQ = "PQ"
    PV = "PV"
    SLACK = "SLACK"
    GEN_INT_VOLT = "GENERATOR_INTERNAL_VOLTAGE"


class BreakerPosition(Enum):
    """
    Breakerposition.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar FIRST_BUS: FIRST BUS.
    :cvar SECOND_BUS: SECOND BUS.
    """
    FIRST_BUS = "FIRST_BUS"
    SECOND_BUS = "SECOND_BUS"


# class Unit(Enum):  # defined twice...
#
"""
#     Unit.
#
"""
#     A = "A"
#     W = "W"
#     KW = "kW"
#     MW = "MW"
#     V = "V"
#     KV = "kV"
#     MV = "MV"
#     VA = "VA"
#     KVA = "kVA"
#     MVA = "MVA"
#     VAR = "VAr"
#     KVAR = "kVAr"
#     MVAR = "MVAr"
#     OHM = "ohm"
#     S = "S"
#     DEG = "deg"
#     RAD = "rad"
#     PERCENT = "PERCENT"
#     MWS_PER_MVA = "MWs/MVA"
#     SCALAR = "SCALAR"

class UnitType(Enum):
    """
    Unittype.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar APPARENT_POWER: APPARENT POWER.
    :cvar ACTIVE_POWER: ACTIVE POWER.
    :cvar REACTIVE_POWER: REACTIVE POWER.
    :cvar CURRENT: CURRENT.
    :cvar VOLTAGE: VOLTAGE.
    :cvar ANGLE: ANGLE.
    :cvar RESISTANCE: RESISTANCE.
    :cvar CONDUCTANCE: CONDUCTANCE.
    :cvar FREQUENCE: FREQUENCE.
    :cvar PER_UNIT: PER UNIT.
    :cvar SCALAR: SCALAR.
    :cvar TIME: TIME.
    """
    APPARENT_POWER = "apparent_power"
    ACTIVE_POWER = "active_power"
    REACTIVE_POWER = "reactive_power"
    CURRENT = "current"
    VOLTAGE = "voltage"
    ANGLE = "angle"
    RESISTANCE = "resistance"
    CONDUCTANCE = "conductance"
    FREQUENCE = "frequence"
    PER_UNIT = "per_unit"
    SCALAR = "scalar"
    TIME = "time"


class Unit(Enum):
    """
    Unit.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar A: A.
    :cvar W: W.
    :cvar KW: KW.
    :cvar MW: MW.
    :cvar V: V.
    :cvar KV: KV.
    :cvar MV: MV.
    :cvar VA: VA.
    :cvar KVA: KVA.
    :cvar MVA: MVA.
    :cvar VAR: VAR.
    :cvar KVAR: KVAR.
    :cvar MVAR: MVAR.
    :cvar OHM: OHM.
    :cvar S: S.
    :cvar MWS_PER_MVA: MWS PER MVA.
    :cvar DEG: DEG.
    :cvar RAD: RAD.
    :cvar HZ: HZ.
    :cvar KHZ: KHZ.
    :cvar MHZ: MHZ.
    :cvar PU: PU.
    :cvar SCALAR: SCALAR.
    :cvar SEC: SEC.
    :cvar MSEC: MSEC.
    """
    A = "A"
    W = "W"
    KW = "kW"
    MW = "MW"
    V = "V"
    KV = "kV"
    MV = "MV"
    VA = "VA"
    KVA = "kVA"
    MVA = "MVA"
    VAR = "VAr"
    KVAR = "kVAr"
    MVAR = "MVAr"
    OHM = "ohm"
    S = "S"
    MWS_PER_MVA = "MWs/MVA"
    DEG = "deg"
    RAD = "rad"
    HZ = "Hz"
    KHZ = "kHz"
    MHZ = "MHz"
    PU = "PU"
    SCALAR = "SCALAR"
    SEC = "s"
    MSEC = "ms"

    @property
    def type(self) -> UnitType:
        """
        Get the type of this unit.
        
        :return: Unit type.
        """
        return UnitType[self.value]


class TransformerType(Enum):
    """
    Transformertype.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar FIXED_REAL_RATIO: FIXED REAL RATIO.
    :cvar ADJUSTABLE_REAL_RATIO: ADJUSTABLE REAL RATIO.
    :cvar DETAILED: DETAILED.
    :cvar QUADRATURE_PHASE: QUADRATURE PHASE.
    :cvar FORTESCUE_GENERAL: FORTESCUE GENERAL.
    :cvar FORTESCUE_DETAILED: FORTESCUE DETAILED.
    :cvar IGNORE_0: IGNORE 0.
    :cvar IGNORE_6: IGNORE 6.
    """
    FIXED_REAL_RATIO = "1"
    ADJUSTABLE_REAL_RATIO = "2"
    DETAILED = "8"
    QUADRATURE_PHASE = "9"
    FORTESCUE_GENERAL = "145"
    FORTESCUE_DETAILED = "147"
    IGNORE_0 = "0"
    IGNORE_6 = "6"


class TransformerRegulatingMode(Enum):
    """
    Transformerregulatingmode.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar NOT_REGULATING: NOT REGULATING.
    :cvar VOLTAGE: VOLTAGE.
    :cvar ACTIVE_FLUX_SIDE_1: ACTIVE FLUX SIDE 1.
    :cvar ACTIVE_FLUX_SIDE_2: ACTIVE FLUX SIDE 2.
    """
    NOT_REGULATING = "N"
    VOLTAGE = "V"
    ACTIVE_FLUX_SIDE_1 = "1"
    ACTIVE_FLUX_SIDE_2 = "2"


class CouplingDeviceOpeningCode(Enum):
    """
    Couplingdeviceopeningcode.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar OPEN: OPEN.
    """
    OPEN = "-"


class GeneratorRegulatingMode(Enum):
    """
    Generatorregulatingmode.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar REGULATING: REGULATING.
    :cvar NOT_REGULATING: NOT REGULATING.
    """
    REGULATING = "V"
    NOT_REGULATING = "N"


class HVDCConverterState(Enum):
    """
    Hvdcconverterstate.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar OFF: OFF.
    """
    OFF = "S"


class OpeningCode(Enum):
    """
    Openingcode.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar BOTH_SIDE_OPEN: BOTH SIDE OPEN.
    :cvar RECEIVING_SIDE_OPEN: RECEIVING SIDE OPEN.
    :cvar SENDING_SIDE_OPEN: SENDING SIDE OPEN.
    """
    BOTH_SIDE_OPEN = "-"
    RECEIVING_SIDE_OPEN = "<"
    SENDING_SIDE_OPEN = ">"


class State(Enum):
    """
    State.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar CONNECTED: CONNECTED.
    :cvar NOT_CONNECTED: NOT CONNECTED.
    """
    CONNECTED = "Y"
    NOT_CONNECTED = "N"


class EventType(Enum):
    """
    Eventtype.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar BREAKER_OPEN: BREAKER OPEN.
    :cvar BREAKER_CLOSE: BREAKER CLOSE.
    :cvar NODE_FAULT: NODE FAULT.
    :cvar NODE_CLEAR: NODE CLEAR.
    :cvar LINE_FAULT: LINE FAULT.
    :cvar LINE_CLEAR: LINE CLEAR.
    :cvar IMPEDANCE_MOD: IMPEDANCE MOD.
    :cvar GENERATOR_START: GENERATOR START.
    :cvar GENERATOR_STOP: GENERATOR STOP.
    :cvar STATOR_OPEN: STATOR OPEN.
    :cvar STATOR_CLOSE: STATOR CLOSE.
    :cvar SETPOINT: SETPOINT.
    :cvar AUTOMATON_SETPOINT: AUTOMATON SETPOINT.
    :cvar MACHINE_SETPOINT_AREA: MACHINE SETPOINT AREA.
    :cvar MACHINE_SETPOINT: MACHINE SETPOINT.
    :cvar TFO_TAP: TFO TAP.
    :cvar LOAD_MODIFICATION: LOAD MODIFICATION.
    :cvar LOAD_VARIATION_AREA: LOAD VARIATION AREA.
    :cvar LOAD_VARIATION_NODE: LOAD VARIATION NODE.
    :cvar LOAD_TIME: LOAD TIME.
    :cvar A14_AUTOMATON: A14 AUTOMATON.
    :cvar DEVICE_ACTIVATION: DEVICE ACTIVATION.
    :cvar BANK_MODIFICATION: BANK MODIFICATION.
    :cvar SCENARIO: SCENARIO.
    :cvar SYSTEM_STATE_SAVE: SYSTEM STATE SAVE.
    :cvar EIGEN_VALUES: EIGEN VALUES.
    :cvar LINEA_EXPORT: LINEA EXPORT.
    :cvar SIMULATION_STOP: SIMULATION STOP.
    :cvar SIMULATION_PAUSE: SIMULATION PAUSE.
    """
    BREAKER_OPEN = 'BRANC OP'
    BREAKER_CLOSE = 'BRANC CL'
    NODE_FAULT = 'FAULTATN'
    NODE_CLEAR = 'CLEARB'
    LINE_FAULT = 'FAULTONL'
    LINE_CLEAR = 'CLEARL'
    IMPEDANCE_MOD = 'MODCAP'
    GENERATOR_START = 'GENER OP'
    GENERATOR_STOP = 'GENER CL'
    STATOR_OPEN = 'STAT  OP'
    STATOR_CLOSE = 'STAT  CL'
    SETPOINT = 'SETPOINT'
    AUTOMATON_SETPOINT = 'SETPMACR'
    MACHINE_SETPOINT_AREA = 'SET AREA'
    MACHINE_SETPOINT = 'SET MACH'
    TFO_TAP = 'TAP   MO'
    LOAD_MODIFICATION = 'LOAD  SW'
    LOAD_VARIATION_AREA = 'LOAD VAR'
    LOAD_VARIATION_NODE = 'LOAD VNO'
    LOAD_TIME = 'LOAD  MT'
    A14_AUTOMATON = 'AUTOM MO'
    DEVICE_ACTIVATION = 'AUTOM AC'
    BANK_MODIFICATION = 'CAP BANK'
    SCENARIO = 'PARA MOD'
    SYSTEM_STATE_SAVE = 'SAVE'
    EIGEN_VALUES = 'EIGNEVAL'
    LINEA_EXPORT = 'LINEAR'
    SIMULATION_STOP = 'STOP'
    SIMULATION_PAUSE = 'PAUSE'


class ElementType(Enum):
    """
    Elementtype.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar BANK: BANK.
    :cvar VSC_CONVERTER: VSC CONVERTER.
    :cvar CSC_CONVERTER: CSC CONVERTER.
    :cvar GENERATOR: GENERATOR.
    :cvar SVC: SVC.
    :cvar LOAD: LOAD.
    """
    BANK = "CA"
    VSC_CONVERTER = "VS"
    CSC_CONVERTER = "CS"
    GENERATOR = "GE"
    SVC = "SV"
    LOAD = "LO"


class TableType(Enum):
    """
    Tabletype.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar TRANSFORMERS: TRANSFORMERS.
    :cvar HVDC_CONVERTERS_RESULTS: HVDC CONVERTERS RESULTS.
    :cvar RESULTS: RESULTS.
    :cvar TRANSFORMERSNODEDATA: TRANSFORMERSNODEDATA.
    :cvar TRANSFORMERTAPDATA: TRANSFORMERTAPDATA.
    """
    TRANSFORMERS = "TRANSFORMERS"
    HVDC_CONVERTERS_RESULTS = "HVDC_CONVERTERS_RESULTS"
    RESULTS = "RESULTS"
    TRANSFORMERSNODEDATA = "TRANSFORMERSNODEDATA"
    TRANSFORMERTAPDATA = "TRANSFORMERTAPDATA"


class FileType(Enum):
    """
    Filetype.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar ECH: ECH.
    :cvar DTA: DTA.
    """
    ECH = "ech"
    DTA = "dta"


class BranchType(Enum):
    """
    Branchtype.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar THREE_WINDING_TRANSFORMER: THREE WINDING TRANSFORMER.
    :cvar COUPLING_DEVICE: COUPLING DEVICE.
    """
    THREE_WINDING_TRANSFORMER = '1'
    COUPLING_DEVICE = '2'



class GeneratorType(Enum):
    """
    Generatortype.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar PQ: PQ.
    :cvar PV: PV.
    :cvar SLACK: SLACK.
    """
    PQ = "PQ"
    PV = "PV"
    SLACK = "SLACK"


class GeneratorSource(Enum):
    """
    Generatorsource.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar nucleair: nucleair.
    :cvar photovol: photovol.
    :cvar step: step.
    :cvar charbon: charbon.
    :cvar eolien: eolien.
    :cvar fictif: fictif.
    :cvar fuel: fuel.
    :cvar turbinag: turbinag.
    :cvar tag: tag.
    :cvar pompage: pompage.
    :cvar autre: autre.
    :cvar cycle_co: cycle co.
    :cvar none: none.
    :cvar unknown: unknown.
    """
    nucleair = "NUCLEAR"
    photovol = "SOLAR"
    step = "HYDRO"
    charbon = "COAL"
    eolien = "WIND"
    fictif = "FICTIVE"
    fuel = "OIL"
    turbinag = "HYDRO"
    tag = "GAS"
    pompage = "HYDRO"
    autre = "OTHER"
    cycle_co = "CYCLE"
    none = "NONE"
    unknown = "UNKNOWN"

def parse_generator_source(value: str | None) -> "GeneratorSource":
    """
    Parse a generator source string into a GeneratorSource enum.
    
    :param value: Raw source string or None.
    :return: Matching GeneratorSource (unknown if not recognized).
    """
    if value is None:
        return GeneratorSource.unknown

    v = value.strip().upper()

    # Match by enum value (e.g. "NUCLEAR")
    for item in GeneratorSource:
        if item.value == v:
            return item

    # Match by enum name (e.g. "nucleair")
    try:
        return GeneratorSource[v.lower()]
    except KeyError:
        return GeneratorSource.unknown


class NetworkState(Enum):
    """
    Networkstate.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar PRE_FAULT: PRE FAULT.
    :cvar DURING_FAULT: DURING FAULT.
    :cvar POST_FAULT: POST FAULT.
    """
    PRE_FAULT = "PRE_FAULT"
    DURING_FAULT = "DURING_FAULT"
    POST_FAULT = "POST_FAULT"


class OMIBSwingState(Enum):
    """
    Omibswingstate.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar BACKWARD: BACKWARD.
    :cvar FORWARD: FORWARD.
    """
    BACKWARD = "BACKWARD"
    FORWARD = "FORWARD"


class OMIBStabilityState(Enum):
    """
    Omibstabilitystate.
    
    Rationale:
        This class supports the EEAC execution flow by encapsulating state or
        behavior used by the pipeline.
    
    :cvar ALWAYS_STABLE: ALWAYS STABLE.
    :cvar ALWAYS_UNSTABLE: ALWAYS UNSTABLE.
    :cvar POTENTIALLY_STABLE: POTENTIALLY STABLE.
    :cvar UNKNOWN: UNKNOWN.
    """
    ALWAYS_STABLE = "ALWAYS STABLE"
    ALWAYS_UNSTABLE = "ALWAYS UNSTABLE"
    POTENTIALLY_STABLE = "POTENTIALLY STABLE"
    UNKNOWN = "UNKNOWN"
