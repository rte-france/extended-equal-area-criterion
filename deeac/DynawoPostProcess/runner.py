"""
Dynawo runtime wrapper.

:module: runner
"""
# Copyright (c) 2020-2026, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from __future__ import annotations

import os
import platform
import subprocess
import tempfile
from enum import Enum
from glob import glob
from typing import Dict, List, Optional


class DynawoOperatingSystem(Enum):
    """
    Supported operating systems for Dynawo binary resolution.

    :cvar LINUX: Linux platform.
    :cvar WINDOWS: Windows platform.
    :cvar MACOS: macOS platform.
    """

    LINUX = "LINUX"
    WINDOWS = "WINDOWS"
    MACOS = "MACOS"


class DynawoBinaryOptions:
    """
    Options used to resolve the Dynawo binary executable.

    :ivar install_root_dir: Dynawo install root containing OS subfolders.
    :ivar install_dir: Dynawo installation directory (contains ``bin/lib/share/ddb``).
    :ivar binary_path: Explicit executable path, if already known.
    :ivar operating_system: Optional explicit operating system override.
    """

    __slots__ = ("install_root_dir", "install_dir", "binary_path", "operating_system")

    def __init__(
        self,
        install_root_dir: Optional[str] = None,
        install_dir: Optional[str] = None,
        binary_path: Optional[str] = None,
        operating_system: Optional[DynawoOperatingSystem] = None,
    ) -> None:
        """
        Initialize Dynawo binary options.

        :param install_root_dir: Dynawo install root containing OS subfolders.
        :param install_dir: Dynawo installation directory.
        :param binary_path: Explicit executable path, if already known.
        :param operating_system: Optional explicit operating system override.
        :return: Return value.
        """
        self.install_root_dir = install_root_dir
        self.install_dir = install_dir
        self.binary_path = binary_path
        self.operating_system = operating_system


class DynawoInstallValidationReport:
    """
    Validation report for a Dynawo installation folder.

    :ivar install_dir: Dynawo installation directory.
    :ivar binary_path: Dynawo executable path.
    :ivar is_valid: True when all required resources exist.
    :ivar errors: Validation error messages.
    """

    __slots__ = ("install_dir", "binary_path", "is_valid", "errors")

    def __init__(
        self,
        install_dir: str,
        binary_path: str,
        is_valid: bool,
        errors: List[str],
    ) -> None:
        """
        Initialize validation report.

        :param install_dir: Dynawo installation directory.
        :param binary_path: Dynawo executable path.
        :param is_valid: Validation success flag.
        :param errors: Validation error messages.
        :return: Return value.
        """
        self.install_dir = install_dir
        self.binary_path = binary_path
        self.is_valid = is_valid
        self.errors = errors

    def to_error_text(self) -> str:
        """
        Build a single-linebreak text describing validation failures.

        :return: Error summary text.
        """
        if self.is_valid:
            return ""
        else:
            lines: List[str] = list()
            lines.append("Dynawo installation validation failed.")
            lines.append(f"install_dir={self.install_dir}")
            lines.append(f"binary_path={self.binary_path}")
            for error_message in self.errors:
                lines.append(f"- {error_message}")
            return "\n".join(lines)


class DynawoProcessResult:
    """
    Raw process result for one Dynawo execution.

    :ivar return_code: Process return code.
    :ivar stdout: Process stdout text.
    :ivar stderr: Process stderr text.
    """

    __slots__ = ("return_code", "stdout", "stderr")

    def __init__(self, return_code: int, stdout: str, stderr: str) -> None:
        """
        Initialize process result.

        :param return_code: Process return code.
        :param stdout: Process stdout.
        :param stderr: Process stderr.
        :return: Return value.
        """
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr


class DynawoRunner:
    """
    Dedicated Dynawo runtime wrapper.

    Rationale:
        Coupling logic should focus on case selection and file generation,
        while runtime concerns (binary path resolution, env vars, process call)
        belong in one dedicated wrapper.

    :ivar _dynawo_binary_path: Resolved Dynawo executable path.
    :ivar _dynawo_install_dir: Resolved Dynawo installation directory.
    """

    __slots__ = ("_dynawo_binary_path", "_dynawo_install_dir")

    def __init__(
        self,
        dynawo_binary_path: Optional[str] = None,
        dynawo_install_dir: Optional[str] = None,
        dynawo_binary_options: Optional[DynawoBinaryOptions] = None,
    ) -> None:
        """
        Initialize the runtime wrapper.

        :param dynawo_binary_path: Optional explicit Dynawo executable path.
        :param dynawo_install_dir: Optional Dynawo install directory.
        :param dynawo_binary_options: Optional binary resolution options.
        :return: Return value.
        """
        if dynawo_binary_path is None:
            options: DynawoBinaryOptions
            if dynawo_binary_options is None:
                options = DynawoBinaryOptions(
                    install_root_dir=default_dynawo_install_root_dir(),
                    install_dir=dynawo_install_dir,
                    binary_path=None,
                    operating_system=None,
                )
            else:
                options = dynawo_binary_options
                if dynawo_install_dir is None:
                    dynawo_install_dir = options.install_dir
                else:
                    dynawo_install_dir = dynawo_install_dir
            self._dynawo_binary_path = resolve_dynawo_binary_path(options)
        else:
            self._dynawo_binary_path = dynawo_binary_path

        if dynawo_install_dir is None:
            self._dynawo_install_dir = resolve_dynawo_install_dir(
                dynawo_binary_path=self._dynawo_binary_path,
                configured_install_dir=None,
            )
        else:
            self._dynawo_install_dir = os.path.abspath(dynawo_install_dir)

    @property
    def dynawo_binary_path(self) -> str:
        """
        Return the resolved Dynawo executable path.

        :return: Dynawo executable path.
        """
        return self._dynawo_binary_path

    @property
    def dynawo_install_dir(self) -> str:
        """
        Return the resolved Dynawo install directory.

        :return: Dynawo install directory path.
        """
        return self._dynawo_install_dir

    def validate_installation(self) -> DynawoInstallValidationReport:
        """
        Validate required Dynawo install resources.

        :return: Validation report.
        """
        return validate_dynawo_installation(
            install_dir=self._dynawo_install_dir,
            binary_path=self._dynawo_binary_path,
        )

    def run_jobs_file(self, jobs_file: str, timeout_seconds: Optional[float] = None) -> DynawoProcessResult:
        """
        Run Dynawo for one jobs file.

        :param jobs_file: Jobs file path.
        :param timeout_seconds: Optional process timeout in seconds.
        :return: Raw process result.
        """
        validation_report = self.validate_installation()
        if validation_report.is_valid:
            pass
        else:
            return DynawoProcessResult(
                return_code=-1,
                stdout="",
                stderr=validation_report.to_error_text(),
            )

        environment = prepare_local_dynawo_runtime_environment(
            base_environment=dict(os.environ),
            dynawo_install_dir=self._dynawo_install_dir,
            dynawo_binary_path=self._dynawo_binary_path,
        )

        command: List[str] = list()
        command.append(self._dynawo_binary_path)
        command.append(jobs_file)
        try:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=environment,
                timeout=timeout_seconds,
            )
            return DynawoProcessResult(
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        except subprocess.TimeoutExpired:
            return DynawoProcessResult(
                return_code=-1,
                stdout="",
                stderr=f"Dynawo execution timeout after {timeout_seconds} seconds.",
            )
        except OSError as os_error:
            return DynawoProcessResult(
                return_code=-1,
                stdout="",
                stderr=f"Dynawo execution failed to start: {os_error}",
            )


def get_current_dynawo_operating_system() -> DynawoOperatingSystem:
    """
    Detect the current operating system for Dynawo binary resolution.

    :return: Detected operating system enum.
    """
    system_name: str = platform.system()
    if system_name == "Linux":
        return DynawoOperatingSystem.LINUX
    else:
        if system_name == "Windows":
            return DynawoOperatingSystem.WINDOWS
        else:
            if system_name == "Darwin":
                return DynawoOperatingSystem.MACOS
            else:
                raise ValueError(f"Unsupported operating system for Dynawo binary resolution: {system_name}")


def resolve_dynawo_binary_path(binary_options: DynawoBinaryOptions) -> str:
    """
    Resolve the Dynawo executable path from binary options.

    :param binary_options: Binary resolution options.
    :return: Resolved Dynawo executable path.
    """
    if binary_options.binary_path is None:
        if binary_options.install_dir is None:
            pass
        else:
            operating_system_from_install_dir: DynawoOperatingSystem
            if binary_options.operating_system is None:
                operating_system_from_install_dir = get_current_dynawo_operating_system()
            else:
                operating_system_from_install_dir = binary_options.operating_system
            candidate_paths_from_install_dir = build_dynawo_binary_candidates_from_install_dir(
                install_dir=binary_options.install_dir,
                operating_system=operating_system_from_install_dir,
            )
            for candidate_path in candidate_paths_from_install_dir:
                if os.path.isfile(candidate_path):
                    return candidate_path
                else:
                    pass
            raise ValueError(f"Dynawo executable not found in install_dir={binary_options.install_dir}")

        install_root_dir = binary_options.install_root_dir
        if install_root_dir is None:
            install_root_dir = default_dynawo_install_root_dir()
        else:
            install_root_dir = install_root_dir

        operating_system = binary_options.operating_system
        if operating_system is None:
            operating_system = get_current_dynawo_operating_system()
        else:
            operating_system = operating_system

        candidate_paths: List[str] = build_dynawo_binary_candidates(install_root_dir, operating_system)
        for candidate_path in candidate_paths:
            if os.path.isfile(candidate_path):
                return candidate_path
            else:
                pass
        raise ValueError(
            f"Dynawo executable not found. install_root_dir={install_root_dir}, operating_system={operating_system.name}"
        )
    else:
        if os.path.isfile(binary_options.binary_path):
            return binary_options.binary_path
        else:
            raise ValueError(f"Dynawo executable not found at binary_path={binary_options.binary_path}")


def build_dynawo_binary_candidates(install_root_dir: str, operating_system: DynawoOperatingSystem) -> List[str]:
    """
    Build candidate binary paths for one operating system.

    :param install_root_dir: Dynawo install root directory.
    :param operating_system: Operating system enum.
    :return: Ordered candidate executable paths.
    """
    candidates: List[str] = list()
    if operating_system == DynawoOperatingSystem.LINUX:
        linux_dir: str = os.path.join(install_root_dir, "Linux")
        candidates.append(os.path.join(linux_dir, "dynawo"))
        candidates.append(os.path.join(linux_dir, "dynawo-1.7.0"))
        candidates.append(os.path.join(install_root_dir, "dynawo", "bin", "dynawo"))
        candidates.append(os.path.join(install_root_dir, "dynawo", "bin", "dynawo-1.7.0"))
        candidates.append(os.path.join(install_root_dir, "bin", "dynawo"))
        candidates.append(os.path.join(install_root_dir, "bin", "dynawo-1.7.0"))
    else:
        if operating_system == DynawoOperatingSystem.WINDOWS:
            windows_dir: str = os.path.join(install_root_dir, "Windows")
            candidates.append(os.path.join(windows_dir, "dynawo.exe"))
        else:
            if operating_system == DynawoOperatingSystem.MACOS:
                macos_dir: str = os.path.join(install_root_dir, "MacOS")
                candidates.append(os.path.join(macos_dir, "dynawo"))
            else:
                raise ValueError(f"Unsupported operating system enum: {operating_system}")
    return candidates


def build_dynawo_binary_candidates_from_install_dir(
    install_dir: str,
    operating_system: DynawoOperatingSystem,
) -> List[str]:
    """
    Build executable candidates from a Dynawo install directory.

    :param install_dir: Dynawo install directory.
    :param operating_system: Operating system enum.
    :return: Candidate executable paths.
    """
    candidates: List[str] = list()
    if operating_system == DynawoOperatingSystem.LINUX:
        candidates.append(os.path.join(install_dir, "bin", "dynawo"))
        candidates.append(os.path.join(install_dir, "bin", "dynawo-1.7.0"))
    else:
        if operating_system == DynawoOperatingSystem.WINDOWS:
            candidates.append(os.path.join(install_dir, "bin", "dynawo.exe"))
        else:
            if operating_system == DynawoOperatingSystem.MACOS:
                candidates.append(os.path.join(install_dir, "bin", "dynawo"))
            else:
                raise ValueError(f"Unsupported operating system enum: {operating_system}")
    return candidates


def resolve_dynawo_install_dir(dynawo_binary_path: str, configured_install_dir: Optional[str]) -> str:
    """
    Resolve Dynawo install directory from explicit config or executable path.

    :param dynawo_binary_path: Dynawo executable path.
    :param configured_install_dir: Explicit install directory, when provided.
    :return: Resolved install directory.
    """
    if configured_install_dir is None:
        binary_parent_dir: str = os.path.dirname(dynawo_binary_path)
        binary_parent_name: str = os.path.basename(binary_parent_dir)
        if binary_parent_name == "bin":
            install_dir: str = os.path.abspath(os.path.join(binary_parent_dir, ".."))
        else:
            install_dir = os.path.abspath(binary_parent_dir)
        return install_dir
    else:
        return os.path.abspath(configured_install_dir)


def validate_dynawo_installation(install_dir: str, binary_path: str) -> DynawoInstallValidationReport:
    """
    Validate the minimum Dynawo install tree expected by the runner.

    :param install_dir: Dynawo install directory.
    :param binary_path: Dynawo executable path.
    :return: Validation report.
    """
    errors: List[str] = list()
    absolute_install_dir: str = os.path.abspath(install_dir)
    absolute_binary_path: str = os.path.abspath(binary_path)

    if os.path.isdir(absolute_install_dir):
        pass
    else:
        errors.append(f"Install directory does not exist: {absolute_install_dir}")

    required_directories: List[str] = list()
    required_directories.append(os.path.join(absolute_install_dir, "lib"))
    required_directories.append(os.path.join(absolute_install_dir, "share"))
    required_directories.append(os.path.join(absolute_install_dir, "ddb"))
    required_directories.append(os.path.join(absolute_install_dir, "share", "xsd"))
    for required_directory in required_directories:
        if os.path.isdir(required_directory):
            pass
        else:
            errors.append(f"Missing directory: {required_directory}")

    dictionaries_mapping_path: str = os.path.join(absolute_install_dir, "share", "dictionaries_mapping.dic")
    if os.path.isfile(dictionaries_mapping_path):
        pass
    else:
        errors.append(f"Missing dictionary mapping file: {dictionaries_mapping_path}")

    if os.path.isfile(absolute_binary_path):
        pass
    else:
        errors.append(f"Dynawo executable not found: {absolute_binary_path}")

    if os.access(absolute_binary_path, os.X_OK):
        pass
    else:
        errors.append(f"Dynawo executable is not executable: {absolute_binary_path}")

    required_solver_patterns: List[str] = list()
    required_solver_patterns.append(os.path.join(absolute_install_dir, "lib", "dynawo_SolverIDA.so*"))
    required_solver_patterns.append(os.path.join(absolute_install_dir, "lib", "dynawo_SolverSIM.so*"))
    required_solver_patterns.append(os.path.join(absolute_install_dir, "lib", "dynawo_SolverTRAP.so*"))
    required_solver_patterns.append(os.path.join(absolute_install_dir, "lib", "dynawo_SolverCommonFixedTimeStep.so*"))
    for required_solver_pattern in required_solver_patterns:
        matches: List[str] = glob(required_solver_pattern)
        if len(matches) > 0:
            pass
        else:
            errors.append(f"Missing solver library matching pattern: {required_solver_pattern}")

    required_runtime_patterns: List[str] = list()
    required_runtime_patterns.append(os.path.join(absolute_install_dir, "lib", "libdynawo_Simulation.so*"))
    required_runtime_patterns.append(os.path.join(absolute_install_dir, "lib", "libdynawo_SimulationCommon.so*"))
    for required_runtime_pattern in required_runtime_patterns:
        matches = glob(required_runtime_pattern)
        if len(matches) > 0:
            pass
        else:
            errors.append(f"Missing runtime library matching pattern: {required_runtime_pattern}")

    is_valid: bool = len(errors) == 0
    return DynawoInstallValidationReport(
        install_dir=absolute_install_dir,
        binary_path=absolute_binary_path,
        is_valid=is_valid,
        errors=errors,
    )


def default_dynawo_install_root_dir() -> str:
    """
    Return the default Dynawo install root used by this repository.

    :return: Default install root path.
    """
    return os.path.dirname(__file__)


def prepare_local_dynawo_runtime_environment(
    base_environment: Dict[str, str],
    dynawo_install_dir: str,
    dynawo_binary_path: str,
) -> Dict[str, str]:
    """
    Prepare local Dynawo runtime environment variables and folders.

    :param base_environment: Base process environment.
    :param dynawo_install_dir: Dynawo install directory.
    :param dynawo_binary_path: Dynawo executable path.
    :return: Environment ready for Dynawo process execution.
    """
    environment: Dict[str, str] = dict(base_environment)

    runtime_install_root: str = dynawo_install_dir
    runtime_share_dir: str = os.path.join(runtime_install_root, "share")
    runtime_xsd_dir: str = os.path.join(runtime_share_dir, "xsd")
    runtime_iidm_xsd_dir: str = runtime_xsd_dir
    runtime_ddb_dir: str = os.path.join(runtime_install_root, "ddb")
    runtime_lib_dir: str = os.path.join(runtime_install_root, "lib")
    dynawo_binary_dir: str = os.path.dirname(dynawo_binary_path)

    existing_ld_library_path: str = environment.get("LD_LIBRARY_PATH", "")
    if existing_ld_library_path == "":
        environment["LD_LIBRARY_PATH"] = f"{runtime_lib_dir}:{dynawo_binary_dir}"
    else:
        environment["LD_LIBRARY_PATH"] = f"{runtime_lib_dir}:{dynawo_binary_dir}:{existing_ld_library_path}"

    if "DYNAWO_INSTALL_DIR" in environment:
        pass
    else:
        environment["DYNAWO_INSTALL_DIR"] = runtime_install_root
    if "DYNAWO_LIBIIDM_INSTALL_DIR" in environment:
        pass
    else:
        environment["DYNAWO_LIBIIDM_INSTALL_DIR"] = runtime_install_root
    if "DYNAWO_LIBIIDM_EXTENSIONS" in environment:
        pass
    else:
        environment["DYNAWO_LIBIIDM_EXTENSIONS"] = ""
    if "DYNAWO_DDB_DIR" in environment:
        pass
    else:
        environment["DYNAWO_DDB_DIR"] = runtime_ddb_dir
    if "DYNAWO_RESOURCES_DIR" in environment:
        pass
    else:
        environment["DYNAWO_RESOURCES_DIR"] = runtime_share_dir
    if "DYNAWO_XSD_DIR" in environment:
        pass
    else:
        environment["DYNAWO_XSD_DIR"] = runtime_xsd_dir
    if "IIDM_XML_XSD_PATH" in environment:
        pass
    else:
        environment["IIDM_XML_XSD_PATH"] = runtime_iidm_xsd_dir
    if "DYNAWO_DICTIONARIES" in environment:
        pass
    else:
        environment["DYNAWO_DICTIONARIES"] = resolve_dynawo_dictionary_mapping_prefix(dynawo_install_dir)
    if "DYNAWO_LOCALE" in environment:
        pass
    else:
        environment["DYNAWO_LOCALE"] = "en_GB"

    return environment


def ensure_local_dynawo_install_tree(dynawo_library_dir: str) -> str:
    """
    Create a local Dynawo install shim tree used by runtime env variables.

    :param dynawo_library_dir: Directory containing local Dynawo binaries/libs.
    :return: Runtime install root directory.
    """
    runtime_root: str = os.path.join(tempfile.gettempdir(), "deeac_dynawo_runtime", "install")
    runtime_bin_dir: str = os.path.join(runtime_root, "bin")
    runtime_lib_dir: str = os.path.join(runtime_root, "lib")
    runtime_ddb_dir: str = os.path.join(runtime_root, "ddb")
    runtime_share_dir: str = os.path.join(runtime_root, "share")
    runtime_xsd_dir: str = os.path.join(runtime_share_dir, "xsd")
    runtime_iidm_xsd_dir: str = os.path.join(runtime_share_dir, "iidm", "xsd")

    os.makedirs(runtime_bin_dir, exist_ok=True)
    os.makedirs(runtime_lib_dir, exist_ok=True)
    os.makedirs(runtime_ddb_dir, exist_ok=True)
    os.makedirs(runtime_xsd_dir, exist_ok=True)
    os.makedirs(runtime_iidm_xsd_dir, exist_ok=True)

    ensure_solver_library_link(dynawo_library_dir, runtime_lib_dir, "dynawo_SolverIDA.so")
    ensure_solver_library_link(dynawo_library_dir, runtime_lib_dir, "dynawo_SolverSIM.so")
    ensure_solver_library_link(dynawo_library_dir, runtime_lib_dir, "dynawo_SolverTRAP.so")
    ensure_solver_library_link(dynawo_library_dir, runtime_lib_dir, "dynawo_SolverCommonFixedTimeStep.so")
    return runtime_root


def ensure_solver_library_link(dynawo_library_dir: str, runtime_lib_dir: str, solver_library_name: str) -> None:
    """
    Ensure one solver shared-library link exists in runtime lib directory.

    :param dynawo_library_dir: Dynawo library directory.
    :param runtime_lib_dir: Runtime lib directory.
    :param solver_library_name: Solver library file name.
    :return: Return value.
    """
    source_path: str = os.path.join(dynawo_library_dir, solver_library_name)
    target_path: str = os.path.join(runtime_lib_dir, solver_library_name)
    if os.path.exists(source_path):
        if os.path.islink(target_path) or os.path.isfile(target_path):
            pass
        else:
            os.symlink(source_path, target_path)
    else:
        pass


def resolve_dynawo_dictionary_mapping_prefix(dynawo_library_dir: str) -> str:
    """
    Resolve or create a dictionary mapping prefix for local Dynawo execution.

    :param dynawo_library_dir: Dynawo binary directory.
    :return: Mapping prefix path without ``.dic`` suffix.
    """
    packaged_prefixes: List[str] = list()
    packaged_prefixes.append(os.path.join(dynawo_library_dir, "share", "dictionaries_mapping"))
    packaged_prefixes.append(os.path.join(dynawo_library_dir, "dictionaries_mapping"))

    for packaged_prefix in packaged_prefixes:
        packaged_mapping_path = f"{packaged_prefix}.dic"
        if os.path.isfile(packaged_mapping_path):
            return packaged_prefix
        else:
            pass

    runtime_dir: str = os.path.join(tempfile.gettempdir(), "deeac_dynawo_runtime")
    os.makedirs(runtime_dir, exist_ok=True)
    runtime_prefix: str = os.path.join(runtime_dir, "dictionaries_mapping")
    runtime_mapping_path: str = f"{runtime_prefix}.dic"
    if os.path.isfile(runtime_mapping_path):
        pass
    else:
        open(runtime_mapping_path, "w").close()
    return runtime_prefix
