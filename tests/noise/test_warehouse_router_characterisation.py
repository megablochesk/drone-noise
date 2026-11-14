"""Characterisation of the warehouse router against its source at the published baseline commit.

Graphs are small 8-neighbour grids like the navigation graph. The weight sets are chosen to stress the
choice between equally short routes, which decides which cells a noise-aware route crosses: random real
weights (no ties), small integers (many ties), zeros (plateaus, as at alpha = 1) and one uniform weight.
"""
import random

import networkx as nx
import numpy as np
import pytest

from noise.navigator.warehouse_dijkstra_router import WarehouseDijkstraRouter
from tests.legacy_reference import load_legacy_module

LEGACY_ROUTER_MODULE = load_legacy_module("noise/navigator/warehouse_dijkstra_router.py")
GRID_ROWS, GRID_COLUMNS = 12, 15
NEIGHBOUR_SHIFTS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
WAREHOUSE_NODES = [(0, 0), (6, 7), (11, 14)]
WEIGHT_RULES = {
    "real weights": lambda generator: generator.uniform(0.5, 3.0),
    "small integers": lambda generator: generator.randint(1, 3),
    "zeros and ones": lambda generator: generator.choice([0.0, 0.0, 1.0]),
    "one weight": lambda generator: 1.0,
}


def build_grid_graph(weight_rule, seed: int, missing_nodes: tuple = ()) -> nx.Graph:
    generator = random.Random(seed)
    graph = nx.Graph()
    nodes = [(row, column) for row in range(GRID_ROWS) for column in range(GRID_COLUMNS) if (row, column) not in missing_nodes]
    graph.add_nodes_from(nodes)
    for row, column in nodes:
        for row_shift, column_shift in NEIGHBOUR_SHIFTS:
            neighbour = (row + row_shift, column + column_shift)
            if neighbour in graph and not graph.has_edge((row, column), neighbour):
                graph.add_edge((row, column), neighbour, weight=weight_rule(generator))
    return graph


def build_routers(graph: nx.Graph, weight="weight"):
    current = WarehouseDijkstraRouter(graph, WAREHOUSE_NODES, weight)
    legacy = LEGACY_ROUTER_MODULE.WarehouseDijkstraRouter(graph, WAREHOUSE_NODES, weight)
    return current, legacy


@pytest.mark.parametrize("rule_name", WEIGHT_RULES)
@pytest.mark.parametrize("seed", [1, 2])
def test_shortest_path_trees_match_the_published_router(rule_name, seed):
    current, legacy = build_routers(build_grid_graph(WEIGHT_RULES[rule_name], seed))
    for warehouse in WAREHOUSE_NODES:
        current_tree, legacy_tree = current._build_spt(warehouse), legacy._build_spt(warehouse)
        np.testing.assert_array_equal(current_tree.pred_idx, legacy_tree.pred_idx)
        np.testing.assert_array_equal(current_tree.dist, legacy_tree.dist)
        assert current_tree.pred_idx.dtype == legacy_tree.pred_idx.dtype
        assert current_tree.dist.dtype == legacy_tree.dist.dtype


@pytest.mark.parametrize("rule_name", WEIGHT_RULES)
def test_routes_match_the_published_router(rule_name):
    """From a warehouse, to a warehouse, and between two cells that are not warehouses."""
    graph = build_grid_graph(WEIGHT_RULES[rule_name], seed=3)
    current, legacy = build_routers(graph)
    generator = random.Random(4)
    cells = list(graph.nodes)
    pairs = [(warehouse, generator.choice(cells)) for warehouse in WAREHOUSE_NODES for _ in range(15)]
    pairs += [(generator.choice(cells), warehouse) for warehouse in WAREHOUSE_NODES for _ in range(15)]
    for start, end in pairs:
        assert current.get_route(start, end) == legacy.get_route(start, end)


def test_cells_cut_off_from_a_warehouse_match_the_published_router():
    """Column 7 is removed except for the warehouse cell (6, 7), so the east half hangs on that one cell and
    an island at (0, 14) cut off by its three neighbours cannot be reached at all."""
    missing = tuple((row, 7) for row in range(GRID_ROWS) if row != 6) + ((0, 13), (1, 13), (1, 14))
    current, legacy = build_routers(build_grid_graph(WEIGHT_RULES["real weights"], seed=5, missing_nodes=missing))
    for warehouse in [(0, 0), (6, 7)]:
        current_tree, legacy_tree = current._build_spt(warehouse), legacy._build_spt(warehouse)
        np.testing.assert_array_equal(current_tree.pred_idx, legacy_tree.pred_idx)
        np.testing.assert_array_equal(current_tree.dist, legacy_tree.dist)
        assert np.isinf(current_tree.dist).sum() == 1


def test_weight_given_as_a_function_matches_the_published_router():
    graph = build_grid_graph(WEIGHT_RULES["small integers"], seed=6)

    def doubled_weight(_start, _end, edge_data) -> float:
        return 2.0 * edge_data["weight"]

    current, legacy = build_routers(graph, weight=doubled_weight)
    for warehouse in WAREHOUSE_NODES:
        np.testing.assert_array_equal(current._build_spt(warehouse).pred_idx, legacy._build_spt(warehouse).pred_idx)
        np.testing.assert_array_equal(current._build_spt(warehouse).dist, legacy._build_spt(warehouse).dist)
