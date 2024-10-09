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

# DEEAC ROADMAP

This file lists the main features that should be added 
to EEAC in the next releases.

## Modelling of Power Electronics

EEAC was born in the late 1980's, at a time when the power systems
were dominated by synchronous generators. Now that Renewable
Energy Sources are becoming an important share of the generation, 
they should no longer be embedded within the loads, and their 
contribution to network stability should be properly modelled.
Same applies to HVDC and Statcom.   

## Reduction of the computation time

So far, most of the effort has been put on achieving a good accuracy with EEAC 
(with respect to a time-domain simulation). 
Therefore there should remain ways to improve the 
computation speed of EEAC.

## Dynawo inputs instead of Eurostag inputs

The current version of EEAC reads Eurostag files as input.
A next version of EEAC should also be able to work using
Dynawo inputs.  
See https://github.com/dynawo/dynawo for more information 
on the Dynaωo suite.

## Minor improvements

- Check the behaviour for faults on a synchronous component that is not the main one.
- Investigate cases where two busbars are connected by at the same time a breaker and 
a line with non 0 impedance.
- Set non-regression tests.
- Verify the good behaviour of EEAC when the critical cluster contains both 
pumping hydro and turbining units.
