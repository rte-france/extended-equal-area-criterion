"""
Example showing manual device model changes after loading a network.

The parser loads the case first. Then normal Python code selects one compiled
device from the network and changes its electrical representation.
"""
from pathlib import Path
from typing import Set

from deeac.IO.eurostag.parse_eurostag import parse_eurostag
from deeac.Models.load import Load
from deeac.Models.matrices.admittance_matrix import AdmittanceMatrix
from deeac.Models.network import Network
from deeac.Models.power_electronics_generator import PowerElectronicsGenerator
from deeac.Models.synchronous_generator import SynchronousGenerator
from deeac.enums import GeneratorElectricalModel, GeneratorType, HvdcElectricalModel


def load_network() -> Network:
    """
    Load the public Eurostag HVDC case.

    The case is loaded with HVDC converters compiled as converter injections so
    that their internal electrical mode can be changed afterwards.

    :return: Loaded DEEAC network.
    """
    repo_root: Path = Path(__file__).resolve().parents[1]
    case_dir: Path = repo_root / "examples" / "eurostag_cases" / "case_3---hvdc"

    # First load the network normally. There is no per-device parser option
    # here; all manual selection happens below on the already-loaded network.
    network: Network = parse_eurostag(
        ech_file=str(case_dir / "fech.ech"),
        dta_file=str(case_dir / "fdta.dta"),
        lf_file=str(case_dir / "fech.lf"),
        hvdc_model=HvdcElectricalModel.CURRENT,
    )

    return network


def print_loaded_device_state(network: Network) -> None:
    """
    Print the current state of the devices changed by the example.

    :param network: Loaded DEEAC network.
    :return: Return value.
    """
    admittance_matrix: AdmittanceMatrix = AdmittanceMatrix(network.buses)
    retained_bus_names: Set[str] = set()
    for bus in admittance_matrix.power_electronics_current_buses:
        retained_bus_names.add(bus.name)

    load: Load = network.load_map["LOA_CC 1"]
    generator: SynchronousGenerator = network.generator_map["GEN_AT 2"]
    converter_generator: PowerElectronicsGenerator = network.power_electronics_generator_map["MRE_REN"]
    print(
        f"{load.name}: connected={load.connected}, "
        f"P={load.active_power:.2f} MW, Q={load.reactive_power:.2f} MVAr"
    )
    print(
        f"{generator.name}: connected={generator.connected}, "
        f"P={generator.active_power:.2f} MW, Q={generator.reactive_power:.2f} MVAr"
    )
    converter_retained: bool = converter_generator.bus.name in retained_bus_names
    print(
        f"{converter_generator.name}: {converter_generator.electrical_model.name}, "
        f"retained_current_bus={converter_retained}"
    )
    for device_name, device in network.hvdc_map.items():
        if isinstance(device, PowerElectronicsGenerator):
            retained: bool = device.bus.name in retained_bus_names
            print(f"{device_name}: {device.electrical_model.name}, retained_current_bus={retained}")
        else:
            print(f"{device_name}: {type(device).__name__}, retained_current_bus=False")


def main() -> None:
    """
    Run the example.

    :return: Return value.
    """
    network: Network = load_network()

    # Converter-generator MRE:
    # the public Eurostag HVDC case has HVDC converters but no regular RES
    # converter generator. Add one manually after loading so the example shows
    # the same electrical-mode switch on a non-HVDC converter device.
    converter_generator: PowerElectronicsGenerator = PowerElectronicsGenerator(
        name="MRE_REN",
        tpe=GeneratorType.PQ,
        bus=network.get_bus_exact("BUS_CS71"),
        active_power=25.0,
        max_active_power=25.0,
        reactive_power=5.0,
        connected=True,
        electrical_model=GeneratorElectricalModel.LOAD,
    )
    network.add_power_electronics_generator(converter_generator)

    print("Before manual change")
    print_loaded_device_state(network)

    # Load example:
    # change the load directly and rebuild its admittance before the next
    # network matrix is created.
    load: Load = network.load_map["LOA_CC 1"]
    load.connected = False
    load.compute_admittance()

    # Generator example:
    # use the synchronous generator setters directly. They recompute the
    # internal voltage used later by the reduced network and OMIB.
    generator: SynchronousGenerator = network.generator_map["GEN_AT 2"]
    generator.active_power = generator.active_power * 0.95
    generator.reactive_power = generator.reactive_power * 0.95

    # Converter-generator electrical-mode example:
    # a converter generator can be moved from passive load-style admittance to
    # retained current-source contribution by changing the object's own mode.
    converter_generator.electrical_model = GeneratorElectricalModel.CURRENT

    # HVDC example:
    # HVDC converters loaded in CURRENT mode are compiled as converter
    # generators. Change one loaded converter to the passive load-style
    # admittance representation directly on the object.
    hvdc: PowerElectronicsGenerator = network.hvdc_map["BUS_B_TE"]
    hvdc.electrical_model = GeneratorElectricalModel.LOAD

    print("After manual change")
    print_loaded_device_state(network)


if __name__ == "__main__":
    main()
else:
    pass
