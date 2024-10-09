# Copyright (c) 2020-2024, RTE (http://www.rte-france.com)
# See AUTHORS.md
# All rights reserved.
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of the deeac project.

import matplotlib.pyplot as plt
from typing import Union, List
from networkx import DiGraph, NetworkXError, dfs_preorder_nodes, draw_planar

from .node import EEACTreeNode, EEACTreeNodeIOType
from deeac.domain.exceptions import (
    DEEACExceptionCollector, EEACTreeLeafException, EEACTreeChildException, EEACTreeNodeException,
    EEACTreeDuplicateIDException
)
from deeac.domain.ports.dtos import eeac_tree as tree_dtos


class EEACTree:

    def __init__(self, name: str, tree_graph: DiGraph):
        """
        Initialize the tree based a tree graph.

        :param tree_graph: Graph whose node are instances of EEACTreeNode. This graph must have been validated, so that
                           the outputs of a node are compatible with its children inputs.
        """
        self._name = name
        self._tree_graph = tree_graph

    @property
    def name(self) -> str:
        """
        Get the tree name.

        :return: The tree name.
        """
        return self._name

    def predecessor(self, node: EEACTreeNode) -> EEACTreeNode:
        """
        Get the predecessor of a given node in the tree.

        :param node: The node foor which the predecessor must be found.
        :return: The predecessor, if it exists, or None if the node is the root node.
        :raise EEACTreeNodeException if the node is not in the tree.
        """
        try:
            return next(parent for parent in self._tree_graph.predecessors(node))
        except NetworkXError:
            raise EEACTreeNodeException(node.id)
        except StopIteration:
            return None

    def deep_first_traversal(self) -> List[EEACTreeNode]:
        """
        Perform a deep-first traversal of the tree.

        :return: A ordered list of nodes according to a deep-first traversal of the tree.
        """
        return list(dfs_preorder_nodes(self._tree_graph, self.root))

    def __getitem__(self, node_id: Union[str, int]) -> EEACTreeNode:
        """
        Define accessor for tree nodes.

        param node_id: Node ID.
        return: The specified node.
        raises: EEACTreeNodeException if the node cannot be found in the tree.
        """
        try:
            return next(node for node in self._tree_graph.nodes if node.id == node_id)
        except StopIteration:
            raise EEACTreeNodeException(node_id)

    @property
    def root(self) -> EEACTreeNode:
        """
        Get the root node of the tree.

        :return: The root node.
        """
        return next(node for node, degree in self._tree_graph.in_degree() if degree == 0)

    @classmethod
    def add_node(
        cls, tree: DiGraph, node_data: tree_dtos.EEACTreeNode, parent: EEACTreeNode = None,
        is_evaluation_tree: bool = False
    ) -> EEACTreeNode:
        """
        Add a node in a tree.

        :param tree: Tree to which the node must be added.
        :param parent: Parent node that must be in the tree. None if the added node is the root node.
        :param node_data: Node data to use to generate the node.
        :param is_evaluation_tree: True if the tree in which the node is added is a critical cluster evaluation tree.
        :return: The node added to the tree
        :raise DEEACExceptionList in case of problem.
        """
        node_ids = {node.id for node in tree.nodes}
        exception_collector = DEEACExceptionCollector()
        with exception_collector:
            # Create node
            eeac_node = EEACTreeNode.create_node(node_data)
            # Check if ID already exists
            if eeac_node.id in node_ids:
                raise EEACTreeDuplicateIDException(eeac_node.id)
            # Check if nodes can be successors in the graph
            if parent is not None:
                try:
                    # Network and output directory are global inputs not provided by a parent tree node
                    unmapped_inputs = [
                        input for input in eeac_node.input_types - parent.output_types
                        if input not in {EEACTreeNodeIOType.NETWORK, EEACTreeNodeIOType.OUTPUT_DIR}
                    ]
                    assert len(unmapped_inputs) == 0
                except AssertionError:
                    raise EEACTreeChildException(parent, eeac_node)

            # Add the node in the tree
            tree.add_node(eeac_node)
            if parent is not None:
                # Node is not the root, link it to its parent node
                tree.add_edge(parent, eeac_node)

            try:
                children = node_data.children
            except AttributeError:
                # No children
                children = None
            if children is None or len(children) == 0:
                if not is_evaluation_tree:
                    # Node is leaf
                    if not eeac_node.can_be_leaf():
                        raise EEACTreeLeafException(eeac_node)
                return eeac_node

        # Cannot go further as node is invalid
        exception_collector.raise_for_exception()

        for child_data in children:
            with exception_collector:
                # Add child node to the tree
                EEACTree.add_node(tree, child_data, eeac_node)
        # Raise if any exception
        exception_collector.raise_for_exception()
        return eeac_node

    def draw_graph(self, output_file: str):
        """
        Generate a graph of the execution tree.

        :param output_file: File in which the graph must be outputted.
        """
        # Colors
        grey = "#B0B0B0"
        black = "#000000"

        # Label nodes
        label_dict = {}
        for node in self._tree_graph.nodes:
            label_dict[node] = node.complete_id

        # Create figure
        fig, ax = plt.subplots(figsize=(25, 15))
        draw_planar(
            self._tree_graph,
            labels=label_dict,
            node_color=grey,
            edge_color=black,
            node_size=1000,
            width=4,
            with_labels=True
        )

        # Save figure
        plt.savefig(output_file)
        plt.close()

    @classmethod
    def create_tree(cls, data: Union[tree_dtos.EEACTree, tree_dtos.EEACClusterEvaluationSequence]) -> 'EEACTree':
        """
        Create an EEAC tree based on EEAC tree data or cluster evaluation sequence data.

        :param tree_data: The tree or sequence data.
        :return: An EEAC tree built based on the data
        :raise: DEEACExceptionList in case of errors.
        """
        tree_graph = DiGraph()
        if type(data) == tree_dtos.EEACTree:
            # Complete tree
            EEACTree.add_node(tree_graph, data.root, None)
            tree_name = data.name
        else:
            # A cluster evaluation sequence is a tree with a single branch
            parent_node = EEACTree.add_node(tree_graph, data.nodes[0], None, True)
            for node in data.nodes[1:]:
                parent_node = EEACTree.add_node(tree_graph, node, parent_node, True)
            tree_name = "Cluster evaluation tree"
        return EEACTree(name=tree_name, tree_graph=tree_graph)
