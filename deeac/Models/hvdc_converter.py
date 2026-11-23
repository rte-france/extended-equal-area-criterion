"""
HVDC converter model selection.

:module: hvdc_converter
"""

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from deeac.Models.bus import Bus

from deeac.Models.generator import PowerElectronicsGenerator, GeneratorType
from deeac.Models.load import Load
from deeac.enums import GeneratorElectricalModel, HvdcElectricalModel


class HvdcConverter:
    """
    HVDC converter element with an explicit numerical representation setting.
    """

    __slots__ = (
        "name",
        "bus",
        "active_power",
        "reactive_power",
        "connected",
        "electrical_model",
    )

    def __init__(
            self,
            name: str,
            bus: "Bus",
            active_power: float,
            reactive_power: float,
            connected: bool,
            electrical_model: HvdcElectricalModel,
    ) -> None:
        """
        Initialize an HVDC converter element.

        :param name: HVDC converter name.
        :param bus: Connected AC bus.
        :param active_power: Active power in MW, using injection convention for
            current-source mode and legacy load convention for load mode.
        :param reactive_power: Reactive power in MVAr.
        :param connected: Connection state.
        :param electrical_model: Numerical model selected for the simulation.
        :return: Return value.
        """
        self.name = name
        self.bus = bus
        self.active_power = active_power
        self.reactive_power = reactive_power
        self.connected = connected
        self.electrical_model = electrical_model

    def compile_numerical_element(self) -> Union[Load, PowerElectronicsGenerator]:
        """
        Compile this HVDC element into the numerical object used by DEEAC.

        :return: Load or current-source converter object matching the setting.
        """
        if self.electrical_model == HvdcElectricalModel.LOAD:
            # Legacy numerical model:
            # the converter contributes as a passive load/admittance in the
            # AC network, matching the old DEEAC behaviour.
            element: Union[Load, PowerElectronicsGenerator] = Load(
                name=self.name,
                bus=self.bus,
                active_power=self.active_power,
                reactive_power=self.reactive_power,
                connected=self.connected,
            )
        else:
            # Current-source numerical model:
            # the converter stays as a retained non-synchronous source so the
            # reduced network keeps its bus and OMIB receives its injection.
            element = PowerElectronicsGenerator(
                name=self.name,
                bus=self.bus,
                active_power=self.active_power,
                max_active_power=abs(self.active_power),
                reactive_power=self.reactive_power,
                connected=self.connected,
                tpe=GeneratorType.PQ,
                electrical_model=GeneratorElectricalModel.CURRENT,
            )
        return element
