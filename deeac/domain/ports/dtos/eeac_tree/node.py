# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

from typing import Optional, Union, List
from pydantic import BaseModel, Field, conlist, constr, PositiveFloat, NonNegativeInt, PositiveInt, confloat
from enum import Enum
from abc import ABC

from pydantic.types import NonNegativeFloat


class EEACTreeNodeType(Enum):
    """
    Different types of EEAC nodes
    """
    CRITICAL_CLUSTERS_IDENTIFIER = "CriticalClustersIdentifier"
    CRITICAL_CLUSTERS_EVALUATOR = "CriticalClustersEvaluator"
    CRITICAL_CLUSTER_SELECTOR = "CriticalClusterSelector"
    GENERATOR_TRAJECTORY_CALCULATOR = "GeneratorTrajectoryCalculator"
    OMIB_TRAJECTORY_CALCULATOR = "OMIBTrajectoryCalculator"
    OMIB = "OMIB"
    EAC = "EAC"


class CriticalClustersIdentifierType(Enum):
    """
    Different types of critical clusters identifiers.
    """
    ACCELERATION = "ACC"
    COMPOSITE = "COMP"
    TRAJECTORY = "TRAJ"
    CONSTRAINED = "CONS"
    DURING_FAULT_TRAJECTORY = "DFT"


class CriticalClusterSelectorType(Enum):
    """
    Different types of critical cluster selectors.
    """
    MIN = "MIN"


class OMIBType(Enum):
    """
    Different OMIB types.
    """
    ZOOMIB = "ZOOMIB"
    RZOOMIB = "RZOOMIB"
    COOMIB = "COOMIB"
    RCOOMIB = "RCOOMIB"
    DOMIB = "DOMIB"
    RDOMIB = "RDOMIB"


class Uncountable(Enum):
    """
    Uncountables
    """
    ALL = "ALL"
    NONE = "NONE"


class OMIBTrajectoryCalculatorType(Enum):
    """
    Different types of OMIB trajectory calculators.
    """
    TAYLOR = "TAYL"
    NUMERICAL = "NUM"


class EEACNodeConfiguration(BaseModel, ABC):
    """
    Parent class of any node configuration.
    Used for typing.
    """
    pass


class CriticalClustersIdentifierConfiguration(EEACNodeConfiguration):
    """
    Configuration of a critical clusters identifier.
    """
    identifier_type: CriticalClustersIdentifierType = Field(..., description="Type of identifier.")
    threshold: Optional[confloat(ge=0, le=1)] = Field(
        default=0.5,
        description="Threshold between 0 and 1 for criterion selection."
    )
    min_cluster_power: Optional[constr(regex="^(\d*\.{0,1}\d+)\s*(MW|kW|W)$")] = Field(
        default="0MW",
        description="Minimum aggregate power a critical cluster candidate should be able to provide."
    )
    threshold_decrement: Optional[confloat(gt=0, le=1)] = Field(
        default=0.1,
        description="Value to subtract to the threshold in case the critical machine candidates "
                    "are not able to provide the minimum active power for the cluster."
    )
    max_number_candidates: Optional[NonNegativeInt] = Field(
        default=0,
        description="Maximum number of candidates. Value 0 means all candidates."
    )
    observation_moment_id: Optional[int] = Field(
        default=-1,
        description="ID of observation moment (with trajectory identifier). Value -1 means maximum angle."
    )
    critical_generator_names: Optional[List[str]] = Field(
        default=None,
        description="Name of the critical generators (with constrained identifier)."
    )
    display_report: Optional[bool] = Field(
        default=False,
        description="True if a report must be displayed for the identifier."
    )
    during_fault_identification_time_step: Optional[NonNegativeFloat] = Field(
        default=0,
        description="Time in milliseconds to compute the angle using Taylor series to identify the critical cluster."
    )
    during_fault_identification_plot_times: Optional[List[NonNegativeFloat]] = Field(
        default=None,
        description="Times in milliseconds to plot the angles using Taylor series."
    )
    significant_angle_variation_threshold: Optional[NonNegativeFloat] = Field(
        default=None,
        description="Angle in degrees used to detect faults that have negligible impact on the dynamic generators."
    )
    try_all_combinations: Optional[bool] = Field(
        default=False,
        description="Whether to create a new candidate cluster by removing generators one by one "
                    "or to try all combinations of generators"
    )
    tso_customization: Optional[str] = Field(
        default="default",
        description="whether to use the default working of an identifier or a version meant for a specific network"
    )
    never_critical_generators: Optional[list] = Field(
        default=None,
        description="generator to never consider as part of the critical cluster"
    )


class CriticalClustersEvaluatorConfiguration(EEACNodeConfiguration):
    """
    Configuration of a critical cluster evaluator.
    """
    evaluation_sequence: 'EEACClusterEvaluationSequence' = Field(
        ...,
        description="Sequence of EEAC tree nodes for evaluation of a critical cluster."
    )
    display_report: Optional[bool] = Field(
        default=False,
        description="True if a report must be displayed for the evaluator."
    )


class CriticalClusterSelectorConfiguration(EEACNodeConfiguration):
    """
    Configuration of a critical cluster selector.
    """
    selector_type: CriticalClusterSelectorType = Field(..., description="Type of selector.")
    display_report: Optional[bool] = Field(
        default=False,
        description="True if a report must be displayed for the selector."
    )


class GeneratorTrajectoryCalculatorConfiguration(EEACNodeConfiguration):
    """
    Configuration of a generator trajectory calculator.
    """
    nb_during_fault_intervals: PositiveInt = Field(..., description="Number of intervals in the during-fault state.")
    nb_post_fault_intervals: PositiveInt = Field(..., description="Number of intervals in the post-fault state.")
    critical_time_shift: Optional[NonNegativeFloat] = Field(
        default=0,
        description="Positive shift (ms) to apply to the critical time."
    )
    display_report: Optional[bool] = Field(
        default=False,
        description="True if a report must be displayed for the trajectory calculator."
    )
    generators_to_plot: Optional[Union[List[str], Uncountable]] = Field(
        default=Uncountable.NONE,
        description="Generators whose rotor angle evolution must be plotted (ALL, NONE or a list of names)."
    )


class OMIBTrajectoryCalculatorConfiguration(EEACNodeConfiguration):
    """
    Configuration of an OMIB trajectory calculator.
    """
    calculator_type: OMIBTrajectoryCalculatorType = Field(..., description="Type of the OMIB trajectory calculator.")
    critical_angle_shift: Optional[NonNegativeFloat] = Field(
        default=0,
        description="Positive shift (deg) to apply to the critical angle."
    )
    display_report: Optional[bool] = Field(
        default=False,
        description="True if a report must be displayed for the trajectory calculator."
    )


class OMIBConfiguration(EEACNodeConfiguration):
    """
    Configuration of an OMIB.
    """
    omib_type: OMIBType = Field(..., description="Type of the OMIB.")
    display_report: Optional[bool] = Field(
        default=False,
        description="True if a report must be displayed for the OMIB."
    )


class EACConfiguration(EEACNodeConfiguration):
    """
    Configuration of EAC.
    """
    angle_increment: PositiveFloat = Field(..., description="Angle increment (deg) when computing critical angle.")
    max_integration_angle: Optional[PositiveFloat] = Field(
        default=360,
        description="Maximum OMIB integration angle (deg)."
    )
    display_report: Optional[bool] = Field(
        default=False,
        description="True if a report must be displayed for the EAC instance."
    )
    plot_area_graph: Optional[bool] = Field(
        default=False,
        description="True if an area plot must be generated by the EACC instance."
    )


class EEACTreeNode(BaseModel):
    """
    Node of an EEAC execution tree.
    """
    name: Optional[str] = Field(None, description="Name of the node.")
    id: Union[int, str] = Field(..., description="Unique identifier if the node in the tree.")
    type: EEACTreeNodeType = Field(..., description="Type of this node.")
    configuration: Union[
        CriticalClustersIdentifierConfiguration,
        CriticalClustersEvaluatorConfiguration,
        CriticalClusterSelectorConfiguration,
        GeneratorTrajectoryCalculatorConfiguration,
        OMIBTrajectoryCalculatorConfiguration,
        OMIBConfiguration,
        EACConfiguration
    ] = Field(..., description="Configuration of this node.")
    children: Optional[List['EEACTreeNode']] = Field(None, description="Children nodes.")


class EEACClusterEvaluationSequenceNode(BaseModel):
    """
    Node of an EEAC execution tree.
    """
    name: Optional[str] = Field(None, description="Name of the node.")
    id: Union[int, str] = Field(..., description="Unique identifier if the node in the tree.")
    type: EEACTreeNodeType = Field(..., description="Type of this node.")
    configuration: Union[
        CriticalClustersIdentifierConfiguration,
        CriticalClustersEvaluatorConfiguration,
        CriticalClusterSelectorConfiguration,
        GeneratorTrajectoryCalculatorConfiguration,
        OMIBTrajectoryCalculatorConfiguration,
        OMIBConfiguration,
        EACConfiguration
    ] = Field(..., description="Configuration of this node.")


class EEACClusterEvaluationSequence(BaseModel):
    """
    Sequence of an EEAC cluster evaluator, consisting in an ordered list of tree nodes without children.
    """
    nodes: conlist(EEACClusterEvaluationSequenceNode, min_items=1) = Field(
        ...,
        description="Nodes in the evaluation sequence"
    )


# Update forward references for circular calls
CriticalClustersEvaluatorConfiguration.update_forward_refs()
EEACTreeNode.update_forward_refs()
