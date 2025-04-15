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
from setuptools import setup, Command

# Package meta-data.
NAME = 'deeac'
PACKAGE = 'deeac'
DESCRIPTION = 'Implementation of DEEAC for transient stability analysis in transmission networks.'
REQUIRES_PYTHON = '>=3.6.4'

# What packages are required for this module to be executed?
REQUIRED = [
    "pydantic==1.10.8",
    "typing_extensions",
    "numpy==1.24.4",
    "networkx>=2.5.1",
    "scipy>=1.5.4",
    "matplotlib>=3.3.4",
    "joblib>=1.4.2"
]

EXTRA_REQUIRED = {
    "tests": [
        "pytest==6.2.5"
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
    description=DESCRIPTION,
    packages=[PACKAGE],
    python_requires=REQUIRES_PYTHON,
    install_requires=REQUIRED,
    extras_require=EXTRA_REQUIRED,
    include_package_data=True,
    zip_safe=False,
    license='Proprietary',
    classifiers=[
        # Trove classifiers
        'License :: Other/Proprietary License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7'
    ],
    cmdclass={
        'upload': UploadCommand,
    },
    # Configure package versioning from source code management tool (i.e. git).
    use_scm_version={
        'local_scheme': lambda *_: "",  # do not prepend dirty-related tag to version
        'write_to': os.path.join('./', PACKAGE.replace(".", "/"), "_version.py")
    },
    setup_requires=['setuptools_scm']
)
