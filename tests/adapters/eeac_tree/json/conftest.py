# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import pytest

from tests import TEST_DATA_FOLDER
from deeac.adapters.eeac_tree.json import JSONTreeParser
from deeac.domain.models import Value, Unit
from deeac.domain.ports.dtos.eeac_tree import (
    EEACTree, EEACTreeNode, EEACTreeNodeType, CriticalClustersIdentifierType, CriticalClusterSelectorType, OMIBType,
    OMIBTrajectoryCalculatorType, CriticalClustersIdentifierConfiguration, CriticalClustersEvaluatorConfiguration,
    CriticalClusterSelectorConfiguration, OMIBTrajectoryCalculatorConfiguration, OMIBConfiguration, EACConfiguration,
    GeneratorTrajectoryCalculatorConfiguration, EEACClusterEvaluationSequenceNode, EEACClusterEvaluationSequence
)


@pytest.fixture
def json_tree_parser() -> JSONTreeParser:
    return JSONTreeParser(f"{TEST_DATA_FOLDER}/eeac_trees/basic_domib_tree.json")


@pytest.fixture
def json_tree_parser_parsing_error() -> JSONTreeParser:
    return JSONTreeParser(f"{TEST_DATA_FOLDER}/eeac_trees/basic_tree_parsing_error.json")


@pytest.fixture
def json_tree_parser_content_error() -> JSONTreeParser:
    return JSONTreeParser(f"{TEST_DATA_FOLDER}/eeac_trees/basic_tree_content_error.json")


@pytest.fixture
def basic_domib_eeac_tree() -> EEACTree:
    root_node = EEACTreeNode(
        id=0,
        name="ACC CCs Identifier",
        type=EEACTreeNodeType.CRITICAL_CLUSTERS_IDENTIFIER,
        configuration=CriticalClustersIdentifierConfiguration(
            identifier_type=CriticalClustersIdentifierType.ACCELERATION,
            threshold=0.5,
            max_number_candidates=1,
            min_cluster_power="1000 kW",
            threshold_decrement=0.2
        ),
        children=[
            EEACTreeNode(
                id=1,
                name="Basic CC Evaluator",
                type=EEACTreeNodeType.CRITICAL_CLUSTERS_EVALUATOR,
                configuration=CriticalClustersEvaluatorConfiguration(
                    evaluation_sequence=EEACClusterEvaluationSequence(
                        nodes=[
                            EEACClusterEvaluationSequenceNode(
                                id=11,
                                name="Basic CC Evaluator - ZOOMIB",
                                type=EEACTreeNodeType.OMIB,
                                configuration=OMIBConfiguration(
                                    omib_type=OMIBType.ZOOMIB
                                )
                            ),
                            EEACClusterEvaluationSequenceNode(
                                id=12,
                                name="Basic CC Evaluator - EAC",
                                type=EEACTreeNodeType.EAC,
                                configuration=EACConfiguration(
                                    angle_increment=1.8,
                                    max_integration_angle=360
                                )
                            ),
                            EEACClusterEvaluationSequenceNode(
                                id=13,
                                name="Basic CC Evaluator - OMIB Trajectory Calculator",
                                type=EEACTreeNodeType.OMIB_TRAJECTORY_CALCULATOR,
                                configuration=OMIBTrajectoryCalculatorConfiguration(
                                    calculator_type=OMIBTrajectoryCalculatorType.TAYLOR
                                )
                            )
                        ]
                    )
                ),
                children=[
                    EEACTreeNode(
                        id=2,
                        name="MIN CC Selector",
                        type=EEACTreeNodeType.CRITICAL_CLUSTER_SELECTOR,
                        configuration=CriticalClusterSelectorConfiguration(
                            selector_type=CriticalClusterSelectorType.MIN
                        ),
                        children=[
                            EEACTreeNode(
                                id=3,
                                name="Generator Trajectory Calculator",
                                type=EEACTreeNodeType.GENERATOR_TRAJECTORY_CALCULATOR,
                                configuration=GeneratorTrajectoryCalculatorConfiguration(
                                    nb_during_fault_intervals=5,
                                    nb_post_fault_intervals=5,
                                    critical_time_shift=10
                                ),
                                children=[
                                    EEACTreeNode(
                                        id=4,
                                        name="DOMIB",
                                        type=EEACTreeNodeType.OMIB,
                                        configuration=OMIBConfiguration(
                                            omib_type=OMIBType.DOMIB
                                        ),
                                        children=[
                                            EEACTreeNode(
                                                id=5,
                                                name="DOMIB EAC",
                                                type=EEACTreeNodeType.EAC,
                                                configuration=EACConfiguration(
                                                    angle_increment=1.8,
                                                    max_integration_angle=360
                                                ),
                                                children=[
                                                    EEACTreeNode(
                                                        id=6,
                                                        name="DOMIB Trajectory Calculator",
                                                        type=EEACTreeNodeType.OMIB_TRAJECTORY_CALCULATOR,
                                                        configuration=OMIBTrajectoryCalculatorConfiguration(
                                                            calculator_type=OMIBTrajectoryCalculatorType.TAYLOR,
                                                            critical_angle_shift=2
                                                        )
                                                    )
                                                ]
                                            )
                                        ]
                                    )
                                ]
                            )
                        ]
                    )
                ]
            )
        ]
    )
    return EEACTree(name="Basic DOMIB tree", root=root_node)
