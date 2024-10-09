<!-- 
     Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
     See AUTHORS.txt
     All rights reserved.
     This Source Code Form is subject to the terms of the Mozilla Public
     License, v. 2.0. If a copy of the MPL was not distributed with this
     file, you can obtain one at http://mozilla.org/MPL/2.0/.
     SPDX-License-Identifier: MPL-2.0
     This file is part of the deeac project.
-->

# Branch configuration

EEAC involves using a sequence of functions to estimate the CCT and the CC. These functions can be organized
into branches, which start with a CCI function and end with a leaf node that provides an estimation of CCT and the CC.
The possible branches can be represented by a directed tree as a set of nodes representing different functions,
and set of edges linking these nodes. Each branch must be stored as a JSON file, listing the nodes and their configuration.

## Nodes

There are 7 possible nodes.

### Critical Cluster Identifier (CCI)

Generates a list of possible CC based on a specified criteria.
It can be based on acceleration, composite, trajectory or during fault identification time step criteria.
The latter returns the best results. It computes the trajectory of every generator at a specified time during the fault
and considers as critical every generator whose angle is beyond the widest absolute gap.

### One Machine Infinite Bus (OMIB)

Returns a model of the Critical Cluster and Non Critical Cluster as an OMIB.

### Equal Area Criterion (EAC)

Applies the Equal Area Criterion to determine the critical clearing angle based on the OMIB curves.
The critical angle is the one for which the acceleration and deceleration areas are almost equal.

### OMIB Trajectory Calculator (OTC)



### Generator Trajectory Calculator (GTC)



### Critical Cluster Selector (CCS)

Selects the CC among all the candidates based on a specified criteria. The only criteria available is MIN, is selects
the CC with the lowest CCT.

### Critical Cluster Evaluator (CCE)

Evaluates the CCs and outputs an estimated CCT for each possible CC.

The CCE function is a combination of other functions, and there are several possible combinations of functions
that can be used to form a CCE. Three possible combinations are shown in Fig.1, each of which involves different
assumptions and models to estimate the CCT and the CC. One combination, CCE (type 1), uses a ZOOMIB or COOMIB
equivalent model to estimate the CCT for each CC, while another combination, CCE (type 2), uses DOMIB model assumptions.
The more complicated combination, CCE (type 3), first estimates the CCT for each CC with ZOOMIB or COOMIB assumptions,
then uses this estimate to obtain generator angle trajectories and update the estimation of CCT with DOMIB assumptions.

Overall, the EEAC tree provides a systematic way of organizing the different functions involved in estimating
the CCT and the CC, and the possible combinations of these functions can be explored to form a CCE.

## Nodes configuration

- CriticalClustersIdentifier
  - identifier_type (MANDATORY): Type of identifier, "ACC", "COMP", "TRAJ", DFT. Use the latter by default
  - threshold: Threshold between 0 and 1 for criterion selection
  - threshold_decrement: Value to subtract to the threshold in case the critical machine candidates are not able to provide the minimum active power for the cluster
  - min_cluster_power: Minimum aggregate power a critical cluster candidate should be able to provide, default 0MW
  - max_number_candidates: Maximum number of candidates. Value 0 means all candidates
  - observation_moment_id: ID of observation moment (with trajectory identifier). Value -1 means maximum angle
  - critical_generator_names: Name of the critical generators (with constrained identifier)
  - display_report: True if a report must be displayed for the identifier
  - during_fault_identification_time_step: Time in milliseconds to compute the angle using Taylor series to identify the critical cluster
  - significant_angle_variation_threshold: angle in degree. Relevant only for DFT. Enable to dismiss faults which have a very weak impact on generators 
  - during_fault_identification_plot_times: Times in milliseconds to plot the angles using Taylor series
  - try_all_combinations: Whether to create a new candidate cluster by removing generators one by one or to try all combinations of generators
- CriticalClustersEvaluator
  - evaluation_sequence (MANDATORY): Sequence of EEAC tree nodes for evaluation of a critical cluster
  - display_report: True if a report must be displayed for the evaluator
  - selector_type: True if a report must be displayed for the selector
- CriticalClusterSelectorConfiguration:
  - selector_type (MANDATORY): Type of selector. "MIN" is the only one available
  - display_report: True if a report must be displayed for the selector
- GeneratorTrajectoryCalculator
  - nb_during_fault_intervals: Number of intervals in the during-fault state
  - nb_post_fault_intervals: Number of intervals in the post-fault state
  - critical_time_shift: Positive shift (ms) to apply to the critical time
  - display_report: True if a report must be displayed for the trajectory calculator
  - generators_to_plot: Generators whose rotor angle evolution must be plotted (ALL, NONE or a list of names)
- OMIBTrajectoryCalculator
  - calculator_type (MANDATORY): Type of the OMIB trajectory calculator
  - critical_angle_shift: Positive shift (deg) to apply to the critical angle
  - display_report: True if a report must be displayed for the trajectory calculator
- OMIB
  - omib_type (MANDATORY): Type of the OMIB
  - display_report: True if a report must be displayed for the OMIB
- EAC
  - angle_increment: Angle increment (deg) when computing critical angle
  - max_integration_angle: Maximum OMIB integration angle (deg)
  - display_report: True if a report must be displayed for the EAC instance
  - plot_area_graph: True if an area plot must be generated by the EACC instance

## Example configuration files

A few configuration files are provided in this folder.

Based on our experience with RTE national case studies (2500 buses), 
we recommend using *branch_1.json* (or its global counterpart) 
which performed best.

- **branch_1_global.json**: will process all fault files 
(seq files) found in seq-files-folder. This is the compact 
configuration, where most of the arguments are listed
within the configuration file and not written in the command line. 
- **branch_1.json**: same configuration as above,
except that most arguments (loadflow data, fault data, dynamic data)
should be written in the command line.   
- **branch_1_forced_CC_selection.json**: useful for debugging purposes.
The critical cluster is given as input by the user.
- **branch_2_case_by_case.json**: a more complex configuration
tree, where a refinement iteration is run after a first CCT 
has been computed.



