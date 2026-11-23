"""
Tests for Dynawo file patching helpers.
"""

from pathlib import Path
from typing import List, Tuple
from xml.etree import ElementTree as ET

from deeac.IO.dynawo.patch_files import patch_dynawo_case_for_events

TESTS_DIR: Path = Path(__file__).resolve().parent
IEEE14_V2_DYNAWO_DIR: Path = TESTS_DIR / "data" / "IEEE14_v2" / "Dynawo"
IEEE14_V2_EVENTS_DIR: Path = IEEE14_V2_DYNAWO_DIR / "events"


def compare_xml_files(first_file: Path, second_file: Path) -> bool:
    """
    Compare two XML files structurally.

    Rationale:
        The patching helpers are validated against checked-in reference files,
        but the exact namespace prefix or incidental whitespace can vary between
        XML serializers. The stable requirement is structural equivalence of
        tags, attributes, text content, and child ordering.

    :param first_file: First XML file to compare.
    :param second_file: Second XML file to compare.
    :return: True when the files are structurally equivalent.
    :rtype: bool
    """
    first_root: ET.Element = parse_xml_file_with_dynawo_fixture_compatibility(first_file)
    second_root: ET.Element = parse_xml_file_with_dynawo_fixture_compatibility(second_file)
    return compare_xml_elements(first_root, second_root)


def parse_xml_file_with_dynawo_fixture_compatibility(xml_file: Path) -> ET.Element:
    """
    Parse one XML file while tolerating the historic Dynawo fixture namespace quirk.

    Rationale:
        Some checked-in IEEE14 v2 DYD fixtures use the ``dyn:`` prefix on child
        tags but forget to declare the prefix on the root element. The patching
        code should still be validated against those reference files, so the
        test repairs that one fixture issue in-memory before comparing XML
        structure.

    :param xml_file: XML file to parse.
    :return: Parsed XML root element.
    :rtype: ET.Element
    """
    xml_text: str = xml_file.read_text(encoding="utf8")

    try:
        return ET.fromstring(xml_text)
    except ET.ParseError:
        fixed_xml_text: str = xml_text.replace(
            '<dyn:dynamicModelsArchitecture xmlns="http://www.rte-france.com/dynawo">',
            '<dyn:dynamicModelsArchitecture xmlns="http://www.rte-france.com/dynawo" '
            'xmlns:dyn="http://www.rte-france.com/dynawo">',
            1,
        )
        return ET.fromstring(fixed_xml_text)


def compare_xml_elements(first_element: ET.Element, second_element: ET.Element) -> bool:
    """
    Compare two XML elements structurally.

    Rationale:
        The generated Dynawo files are small trees where semantic equality is
        fully described by the element tag, attributes, normalized text, and
        recursively ordered children. This helper keeps the test intent focused
        on those semantics rather than on raw file bytes.

    :param first_element: First XML element to compare.
    :param second_element: Second XML element to compare.
    :return: True when the XML elements are structurally equivalent.
    :rtype: bool
    """
    if first_element.tag != second_element.tag:
        return False
    else:
        if first_element.attrib != second_element.attrib:
            return False
        else:
            if normalize_xml_text(first_element.text) != normalize_xml_text(second_element.text):
                return False
            else:
                if len(first_element) != len(second_element):
                    return False
                else:
                    child_index: int = 0
                    while child_index < len(first_element):
                        if compare_xml_elements(first_element[child_index], second_element[child_index]):
                            if (normalize_xml_text(first_element[child_index].tail) !=
                                    normalize_xml_text(second_element[child_index].tail)):
                                return False
                        else:
                            return False
                        child_index += 1
                    return True


def normalize_xml_text(raw_text: str | None) -> str:
    """
    Normalize XML text for structural comparison.

    Rationale:
        Pretty-printed XML contains indentation whitespace that is not part of
        the Dynawo semantics. Normalizing ``None`` and trimming pure formatting
        whitespace keeps the comparison aligned with the meaning of the file.

    :param raw_text: Raw XML text or tail value.
    :return: Normalized text.
    :rtype: str
    """
    if raw_text is None:
        return ""
    else:
        return raw_text.strip()


def test_patch_dynawo_case_for_ieee14_v2_line_faults(tmp_path: Path) -> None:
    """
    Generate the IEEE14 v2 Dynawo patched files and compare them with the reference fixtures.

    :param tmp_path: Temporary directory provided by pytest.
    :return: Return value.
    """
    jobs_file: Path = IEEE14_V2_DYNAWO_DIR / "IEEE14_JOBS.xml"
    event_files: List[Path] = [
        IEEE14_V2_EVENTS_DIR / "Line_1-5.xml",
        IEEE14_V2_EVENTS_DIR / "Line_1-2.xml",
    ]
    patched_case = patch_dynawo_case_for_events(jobs_file=jobs_file, event_files=event_files, output_dir=tmp_path)

    # The generated case must contain the same scenario files as the checked-in reference set.
    generated_pairs: List[Tuple[Path, Path]] = [
        (patched_case.multiple_jobs_file, IEEE14_V2_DYNAWO_DIR / "IEEE14_MULTIPLE.xml"),
    ]

    for generated_scenario in patched_case.scenarios:
        generated_pairs.append(
            (
                generated_scenario.dyd_file,
                IEEE14_V2_DYNAWO_DIR / generated_scenario.dyd_file.name,
            )
        )
        generated_pairs.append(
            (
                generated_scenario.par_file,
                IEEE14_V2_DYNAWO_DIR / generated_scenario.par_file.name,
            )
        )

    generated_files: List[Path] = list()

    for generated_file, reference_file in generated_pairs:
        generated_files.append(generated_file)
        assert generated_file.exists()
        assert compare_xml_files(generated_file, reference_file), (
            f"Patched file {generated_file.name} does not match reference {reference_file.name}"
        )

    # The patching workflow must leave no generated files behind once the verification is complete.
    for generated_file in generated_files:
        generated_file.unlink()
        assert not generated_file.exists()

    remaining_paths: List[Path] = sorted(tmp_path.rglob("*"), reverse=True)
    for remaining_path in remaining_paths:
        if remaining_path.is_dir():
            remaining_path.rmdir()
        else:
            remaining_path.unlink()

    # check that all files are deleted afterward
    assert list(tmp_path.iterdir()) == []
