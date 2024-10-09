<!-- 
     Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
     See AUTHORS.md
     All rights reserved.
     This Source Code Form is subject to the terms of the Mozilla Public
     License, v. 2.0. If a copy of the MPL was not distributed with this
     file, you can obtain one at http://mozilla.org/MPL/2.0/.
     SPDX-License-Identifier: MPL-2.0
     This file is part of the deeac project.
-->

# DEEAC

[![MPL-2.0 License](https://img.shields.io/badge/license-MPL_2.0-blue.svg)](https://www.mozilla.org/en-US/MPL/2.0/)

Python implementation of the Dynamic Extended Equal Area Criterion (DEEAC) to analyze the transient stability in transmission networks.

## Table of Contents

- [About DEEAC](#about-deeac)
- [Contributors](#contributors)
- [License](#license)
- [Reference paper](#reference-paper)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
  * [Command line](#command-line)
  * [Outputs](#outputs)  
- [Code Architecture](#code-architecture)
- [Getting started](#getting-started)

## About DEEAC

For transient stability analysis (TSA) of a multi-machine power system, the extended equal area criterion (EEAC) method
applies the classic equal area criterion (EAC) concept to an approximate one-machine infinite bus (OMIB) equivalent
of the system to find the critical clearing angle. The system critical clearing time (CCT) can then be obtained
by numerical integration of OMIB equations. The EEAC method was proposed in the 1980s and 1990s as a substitute
for time-domain simulation for transmission system operator (TSO) to provide fast TSA with
the limited computational power of those days. To ensure the secure operation of the power system,
TSOs have to identify and prevent potential critical scenarios by offline analyses of a few dangerous ones.
These days, due to increased uncertainties in electrical power systems, the number of these critical scenarios
is increasing tremendously, calling for fast TSA techniques once more. Among them, the EEAC is a unique approach
that provides not only valuable information, but also a graphical representation of system dynamics.

The EEAC method consists of four main stages:  
- Critical clusters identification (CCI) to identify the critical machines (CMs) and to form a number
of possible critical clusters (CCs) of synchronous machines. It can be based on acceleration, composite, 
during-fault trajectory, or (post-fault) trajectory criteria.
- OMIB model formation for each CC, it can be of type zero offset OMIB (ZOOMIB), constant offset OMIB (COOMIB), or dynamic OMIB (DOMIB).
- EAC for calculation of the critical clearing angle (CCA) of each OMIB equivalent model
- Numerical integration of each OMIB equation to find the CCT corresponding to the OMIB CCA that can be based on Taylor series or numerical integration.

Finally, EEAC selects the CC with the smallest CCT as the true CC.

These functions can be combined in different ways to form a branch of functions to make an estimation of the CCT and the CC.

## Contributors

This code is the fruit of a joint project between *Haulogy Intelligent Systems Solutions* and
*RTE*. The main contributors are listed in AUTHORS.md.

## License

This project and is licensed under the terms of the 
[Mozilla Public License V2.0](http://mozilla.org/MPL/2.0). 
See [LICENSE](LICENSE.txt) for more information.

## Reference paper

If you use this EEAC implementation in your work or research, 
it would be appreciated if you could quote the following paper 
in your publications or presentations:

```
A. Bahmanyar, D. Ernst, Y. Vanaubel, Q. Gemine, C. Pache and P. Panciatici, 
“Extended Equal Area Criterion Revisited: a direct method for fast transient stability analysis”,
published in Energies 2021, 14.
```

## Requirements

* Python >= 3.6.4

## Installation

The package and its dependencies should be installed in a python virtual environment. First, create a virtual environment called `venv`:

```bash
python -m venv venv
```

Activate the virtual environment:

```bash
source venv/bin/activate
```

Make sure that `pip` is up-to-date:

```bash
(venv) pip install --upgrade pip
```

Pull the git repository and install DEEAC and its dependencies by running the following command from the cloned repository:

```bash
(venv) pip install -e .[tests]
```

If you don't plan to run the tests, you can omit installing the test dependencies by running instead `(venv) pip install -e .`

## Usage

### Command line

The regular way to run EEAC is as follows:

```bash
python -m deeac \
# Eurostag static network file
-e /PATH/TO/STATIC/NETWORK/DATA/fech.ech \
# Eurostag dynamic network file
-d /PATH/TO/DYNAMIC/NETWORK/DATA/fdta.dta \
# Load flow data
-l /PATH/TO/LOADFLOW/fech.lf \
# Eurostag sequence file describing the fault
-s /PATH/TO/SEQFILE.seq \
# Tree branch describing the execution path of DEEAC
-t /PATH/TO/TREE/BRANCH.json \
# Optional output folder saving the intermediary results and plots
-o /PATH/TO/OUTPUT/FOLDER \
# Optional output file saving the critical cluster and the CCT
-j /PATH/TO/OUTPUT/FILE.json \
# Optional list of never critical generators
-n GENERATOR \
# Verbose
-v \
# Rewrite the output folder
-r
```

A more compact call is possible provided that the arguments 
listed above are embedded within the json configuration file. 
Then, the command line becomes:

```
python -m deeac -g branch.json
```

### Outputs

DEEAC prints out report presenting the main results which can be saved as json, and it can also produce plots
of the graph and area plots of the EEAC itself.

#### Report

```
	Configuration:
		Type of selector: MinCriticalClusterSelector
	Inputs:
		Cluster N:
            ...
	Outputs:
        Critical generators: [GENERATOR NAMES]
        Critical angle: X.XXX rad [X.XXX deg]
        Critical time: XXX.XXX ms
        Maximum angle: X.XXX rad [XXX.XXX deg]
        Maximum time: XXX.XXX ms
        OMIB stability state: [STABILITY STATE]
        OMIB swing state: [FORWARD OR BACKWARD]

	* Generators disconnected from the main network component due to the mitigations: [GENERATOR NAMES]
Execution times:
	> Input execution tree file reading: X.XXX seconds
	> Input data files reading: X.XXX seconds
	> Event processing: X.X seconds
	> EEAC tree execution: X.XXX seconds
	> Total time: XX.XXX seconds
```

#### PDF plots

A plots of the generator angle trajectory can be generated, as well as a plot of the EAC area.
See the section _Nodes configuration_, section GTC and EAC.

#### Json critical results

Output file that can be set as input in the command line, contains only the critical results of the
critical_cluster_selector_node or omib_trajectory_calculator: node id, CCT, OMIB stability state, critical cluster

#### PDF execution tree

A graphical representation of the branch, chaining the nodes to one another.

#### TXT files

A txt file is generated per node, containing its report, detailing its inputs, outputs, and execution status.
Added together they represent the report mentioned above.

## Code Architecture

DEEAC follows the hexagonal design pattern. It defines a perimeter, called the "domain", representing the inner part
of the software. It contains a data model describing the network, load flows, event, etc..., and methods, called
"services", communicating with each other and working with data only from the data model. There is then a third
type of component, called the ports, which are abstract classes templating the communication method between the domain
and the outside world. Services using data from outside model can use implementations of these abstract classes, called
"adapters", specifically designed for their specific tasks. Namely, each data parsing services are using adapter code
design to parse Eurostag input data, and convert them into a network as defined by the data model.

## Getting started

The folder *examples/eurostag_cases* contains a bunch of very simple
cases that can be run with EEAC. Each case contains:
* a **.ech** file, which contains the topology data,
* a **.lf** file, which contains the power flow output data,
* a **.dta** file, which contains the dynamic data, namely the 
inertias and transient reactances,
* a **.seq file**, which list the sequence of events for the fault 
(location of the fault and action of breakers),
* a **.json** file, which describes the DEEAC configuration,
* a **cmd_eeac.txt** file, which contain the command line to run
in the terminal (remember to source the virtual environment first!).
 
Besides, the folder *examples/configuration_files* contains several DEEAC 
configuration files that could be used in order to run EEAC.
*branch_1.json* or *branch_1_global.json* are recommended. 
