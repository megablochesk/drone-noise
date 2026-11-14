"""Shortest-path tree on edge arrays. Hand-built graph:

    0 --1-- 1 --1-- 2 --5-- 3        4 (isolated)
     \\______2______/

Distances from node 0 are 0, 1, 2, 7. Node 2 is reached equally well from node 0 (direct, 2) and from node 1
(1 + 1); the published router keeps the candidate parent with the lowest index, here node 0.
"""
import numpy as np

from noise.navigator.shortest_path_tree import NO_PARENT, calculate_shortest_path_tree

EDGE_STARTS = np.array([0, 1, 0, 2])
EDGE_ENDS = np.array([1, 2, 2, 3])
EDGE_WEIGHTS = np.array([1.0, 1.0, 2.0, 5.0])
NUMBER_OF_NODES = 5


def test_distances_and_lowest_index_parents_of_the_hand_built_graph():
    parents, distances = calculate_shortest_path_tree(NUMBER_OF_NODES, EDGE_STARTS, EDGE_ENDS, EDGE_WEIGHTS, source=0)
    np.testing.assert_array_equal(distances, [0.0, 1.0, 2.0, 7.0, np.inf])
    np.testing.assert_array_equal(parents, [0, 0, 0, 2, NO_PARENT])


def test_edges_are_undirected():
    """From node 3 everything is reached backwards: 3 -> 2 (5), then 0 (7) and 1 (6)."""
    parents, distances = calculate_shortest_path_tree(NUMBER_OF_NODES, EDGE_STARTS, EDGE_ENDS, EDGE_WEIGHTS, source=3)
    np.testing.assert_array_equal(distances, [7.0, 6.0, 5.0, 0.0, np.inf])
    np.testing.assert_array_equal(parents, [2, 2, 3, 3, NO_PARENT])


def test_zero_weight_edges_are_edges():
    """With the 0-1 edge free, node 1 is at distance 0 and node 2 at 1 through node 1."""
    weights = np.array([0.0, 1.0, 2.0, 5.0])
    parents, distances = calculate_shortest_path_tree(NUMBER_OF_NODES, EDGE_STARTS, EDGE_ENDS, weights, source=0)
    np.testing.assert_array_equal(distances, [0.0, 0.0, 1.0, 6.0, np.inf])
    np.testing.assert_array_equal(parents, [0, 0, 1, 2, NO_PARENT])
