"""Shortest-path tree of an undirected graph given as edge arrays.

Distances come from a compiled Dijkstra. The parent of a node is then chosen exactly as the published router
chose it from the predecessor lists of NetworkX: among all neighbours that give the node its distance, the
one with the lowest index. Which equally short route is taken therefore does not depend on the algorithm.
"""
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

NO_PARENT = -1


def find_lowest_index_parents(
        number_of_nodes: int, starts: np.ndarray, ends: np.ndarray, weights: np.ndarray, distances: np.ndarray, source: int
) -> np.ndarray:
    """`starts`, `ends` and `weights` list every edge in both directions."""
    end_is_reached = np.isfinite(distances[ends])
    gives_the_distance = end_is_reached & (distances[starts] + weights == distances[ends])

    parents = np.full(number_of_nodes, number_of_nodes, dtype=np.int64)
    np.minimum.at(parents, ends[gives_the_distance], starts[gives_the_distance])
    parents[parents == number_of_nodes] = NO_PARENT
    parents[source] = source
    return parents


def build_adjacency(number_of_nodes: int, edge_starts: np.ndarray, edge_ends: np.ndarray, edge_weights: np.ndarray):
    """Both directions of every edge, and the sparse matrix of them."""
    starts = np.concatenate([edge_starts, edge_ends])
    ends = np.concatenate([edge_ends, edge_starts])
    weights = np.concatenate([edge_weights, edge_weights]).astype(np.float64)
    return starts, ends, weights, csr_matrix((weights, (starts, ends)), shape=(number_of_nodes, number_of_nodes))


def calculate_shortest_path_tree(
        number_of_nodes: int, edge_starts: np.ndarray, edge_ends: np.ndarray, edge_weights: np.ndarray, source: int
) -> tuple[np.ndarray, np.ndarray]:
    """Parent and distance of every node; unreachable nodes have NO_PARENT and an infinite distance."""
    starts, ends, weights, adjacency = build_adjacency(number_of_nodes, edge_starts, edge_ends, edge_weights)
    distances = dijkstra(adjacency, directed=True, indices=source)
    return find_lowest_index_parents(number_of_nodes, starts, ends, weights, distances, source), distances


def calculate_search_tree(
        number_of_nodes: int, edge_starts: np.ndarray, edge_ends: np.ndarray, edge_weights: np.ndarray, source: int
) -> np.ndarray:
    """Parents as the search itself found them: a tree even where edges of zero cost make the lowest-index rule loop."""
    _, _, _, adjacency = build_adjacency(number_of_nodes, edge_starts, edge_ends, edge_weights)
    _, predecessors = dijkstra(adjacency, directed=True, indices=source, return_predecessors=True)
    parents = np.where(predecessors < 0, NO_PARENT, predecessors).astype(np.int64)
    parents[source] = source
    return parents
