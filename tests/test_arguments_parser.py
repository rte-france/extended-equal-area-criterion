"""
Focused tests for Eurostag argument parsing.
"""
from pathlib import Path

from deeac.IO.arguments_parser import load_global_configuration, parse_eurostag_arguments


def _touch(path: Path) -> None:
    """
    Create an empty file used by argument-parser path checks.

    :param path: File path to create.
    :return: Return value.
    """
    path.write_text("", encoding="utf-8")


def test_parse_eurostag_arguments_reads_supported_options(tmp_path: Path) -> None:
    """
    CLI parsing should expose the currently supported Eurostag options.
    """
    ech_file = tmp_path / "case.ech"
    dta_file = tmp_path / "case.dta"
    lf_file = tmp_path / "case.lf"
    seq_file = tmp_path / "case.seq"
    execution_tree_file = tmp_path / "plan.json"

    for path in (ech_file, dta_file, lf_file, seq_file, execution_tree_file):
        _touch(path)

    config = parse_eurostag_arguments(
        [
            "-e", str(ech_file),
            "-d", str(dta_file),
            "-l", str(lf_file),
            "-s", str(seq_file),
            "-t", str(execution_tree_file),
            "-c", "3",
            "-i", "12.5",
            "-p", "17",
            "-v",
            "-r",
            "-w", "Y",
        ]
    )

    assert config.ech_file == str(ech_file)
    assert config.dta_file == str(dta_file)
    assert config.lf_file == str(lf_file)
    assert config.seq_file == str(seq_file)
    assert config.execution_tree_file == str(execution_tree_file)
    assert config.cores == 3
    assert config.island_threshold == 12.5
    assert config.protection_delay == 17.0
    assert config.verbose is True
    assert config.rewrite is True
    assert config.warn is True


def test_load_global_configuration_reads_supported_keys(tmp_path: Path) -> None:
    """
    Global configuration loading should expose the currently supported keys.
    """
    ech_file = tmp_path / "case.ech"
    dta_file = tmp_path / "case.dta"
    lf_file = tmp_path / "case.lf"
    seq_file = tmp_path / "case.seq"
    execution_tree_file = tmp_path / "plan.json"

    for path in (ech_file, dta_file, lf_file, seq_file, execution_tree_file):
        _touch(path)

    config_file = tmp_path / "config.json"
    config_file.write_text(
        (
            "{\n"
            '  "ech-file": "case.ech",\n'
            '  "dta-file": "case.dta",\n'
            '  "lf-file": "case.lf",\n'
            '  "seq-file": "case.seq",\n'
            '  "execution-tree-file": "plan.json",\n'
            '  "cores": 4,\n'
            '  "island-threshold": 9.5,\n'
            '  "protection-delay": 22,\n'
            '  "rewrite": true,\n'
            '  "verbose": true,\n'
            '  "warn": true\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    config = load_global_configuration(str(config_file))

    assert config.ech_file == str(ech_file)
    assert config.dta_file == str(dta_file)
    assert config.lf_file == str(lf_file)
    assert config.seq_file == str(seq_file)
    assert config.execution_tree_file == str(execution_tree_file)
    assert config.cores == 4
    assert config.island_threshold == 9.5
    assert config.protection_delay == 22.0
    assert config.rewrite is True
    assert config.verbose is True
    assert config.warn is True
