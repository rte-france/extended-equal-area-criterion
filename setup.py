# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import os
import sys
from pathlib import Path
from setuptools import setup, Command, find_packages

# Package meta-data.
NAME = 'deeac'
PACKAGE = 'deeac'
DESCRIPTION = 'Implementation of DEEAC for transient stability analysis in transmission networks.'
REQUIRES_PYTHON = '>=3.10.0'


def read_version() -> str:
    """
    Read the package version from deeac/__version__.py.
    
    :return: Version string.
    """
    version_path = Path(__file__).resolve().parent / PACKAGE / "__version__.py"
    namespace = {}
    exec(version_path.read_text(encoding="utf-8"), namespace)
    return namespace["__version__"]

# What packages are required for this module to be executed?
REQUIRED = [
    "typing_extensions",
    "numpy>=2.2.0",
    "pandas",
    "networkx>=2.5.1",
    "scipy>=1.5.4",
    "matplotlib>=3.3.4",
    "joblib>=1.4.2",
    "pypowsybl>=1.13.0"
]

EXTRA_REQUIRED = {
    "tests": [
        "pytest>=6.2.5"
    ]
}


class UploadCommand(Command):
    """Support setup.py upload."""

    description = 'Build and publish the package.'
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        self.status('Building Source distribution…')
        os.system('{0} setup.py sdist'.format(sys.executable))

        self.status('Uploading the package to PyPI via Twine…')
        rc = os.system(
            'twine upload '
            '--repository-url https://priv.blacklight-analytics.com:8001/simple/ '
            'dist/*'
        )

        sys.exit(rc)


setup(
    name=NAME,
    version=read_version(),
    description=DESCRIPTION,
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    packages=find_packages(
        exclude=(
            "tests",
            "tests_private",
            "trunk",
            "venv311",
            "venv312",
            "build",
            "dist",
            "examples",
            "docs",
        )
    ),
    python_requires=REQUIRES_PYTHON,
    install_requires=REQUIRED,
    extras_require=EXTRA_REQUIRED,
    include_package_data=True,
    zip_safe=False,
    license='MPL-2.0',
    entry_points={
        "console_scripts": [
            "deeac=deeac.main:run",
        ]
    },
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12'
    ],
    cmdclass={
        'upload': UploadCommand,
    }
)
