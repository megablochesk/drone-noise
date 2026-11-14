"""The navigation grid as arrays: cells joined to their eight neighbours, and the cost of flying along each edge."""
import math
import random

import networkx as nx
import numpy as np
import pytest

from noise.navigator.cost_function_generator import make_mixed_distance_noise_weight
from noise.navigator.navigation_grid import (
    build_navigation_grid,
    calculate_mixed_edge_costs,
    read_navigation_grid_from_graph,
)
from noise.noise_graph_builder import _connect_adjacent_cells

CELL_SIZE_M = 100
DIAGONAL_M = 100 * math.sqrt(2.0)


def build_square_grid(noise_levels_db):
    """Cells (0,0), (0,1), (1,0), (1,1), given in reverse order to show that the grid sorts them."""
    rows, columns = np.array([1, 1, 0, 0]), np.array([1, 0, 1, 0])
    eastings, northings = 1_000.0 + 100.0 * columns, 5_000.0 + 100.0 * rows
    return build_navigation_grid(rows, columns, eastings, northings, np.array(noise_levels_db)[::-1], CELL_SIZE_M)


def list_edges(grid) -> dict[tuple[int, int], float]:
    return {
        (min(start, end), max(start, end)): length
        for start, end, length in zip(grid.edge_starts.tolist(), grid.edge_ends.tolist(), grid.edge_lengths_m.tolist())
    }


def test_cells_are_sorted_by_row_and_column():
    grid = build_square_grid([40.0, 50.0, 60.0, 80.0])

    assert list(zip(grid.rows.tolist(), grid.columns.tolist())) == [(0, 0), (0, 1), (1, 0), (1, 1)]
    assert grid.eastings.tolist() == [1_000.0, 1_100.0, 1_000.0, 1_100.0]
    assert grid.northings.tolist() == [5_000.0, 5_000.0, 5_100.0, 5_100.0]
    assert grid.noise_levels_db.tolist() == [40.0, 50.0, 60.0, 80.0]


def test_four_cells_in_a_square_have_four_sides_and_two_diagonals_each_listed_once():
    grid = build_square_grid([40.0, 50.0, 60.0, 80.0])

    assert len(grid.edge_starts) == 6
    assert list_edges(grid) == pytest.approx({
        (0, 1): 100.0, (2, 3): 100.0, (0, 2): 100.0, (1, 3): 100.0, (0, 3): DIAGONAL_M, (1, 2): DIAGONAL_M,
    })


def test_an_edge_carries_the_mean_level_of_its_two_cells():
    grid = build_square_grid([40.0, 50.0, 60.0, 80.0])
    level_by_edge = {
        (min(start, end), max(start, end)): level
        for start, end, level in zip(grid.edge_starts.tolist(), grid.edge_ends.tolist(), grid.edge_noise_levels_db.tolist())
    }

    assert level_by_edge == {(0, 1): 45.0, (2, 3): 70.0, (0, 2): 50.0, (1, 3): 65.0, (0, 3): 60.0, (1, 2): 55.0}


def test_a_missing_cell_leaves_only_the_edges_between_existing_cells():
    """Cells (0,0), (0,1), (1,1): two sides and one diagonal."""
    rows, columns = np.array([0, 0, 1]), np.array([0, 1, 1])
    grid = build_navigation_grid(rows, columns, 100.0 * columns, 100.0 * rows, np.array([40.0, 40.0, 40.0]), CELL_SIZE_M)

    assert list_edges(grid) == pytest.approx({(0, 1): 100.0, (1, 2): 100.0, (0, 2): DIAGONAL_M})


def test_mixed_cost_weighs_length_in_cells_against_the_normalised_level():
    """Levels span 40-80 dB. Edge (0,0)-(0,1): level 45 dB -> (45 - 40) / 40 = 0.125; one cell long.

    alpha = 0.25: 0.75 x 1 + 0.25 x 0.125 = 0.78125. Diagonal (0,0)-(1,1): level 60 dB -> 0.5;
    0.75 x sqrt(2) + 0.25 x 0.5.
    """
    grid = build_square_grid([40.0, 50.0, 60.0, 80.0])
    cost_by_edge = dict(zip(list_edges(grid), calculate_mixed_edge_costs(grid, alpha=0.25).tolist()))

    assert cost_by_edge[(0, 1)] == pytest.approx(0.78125, abs=1e-12)
    assert cost_by_edge[(0, 3)] == pytest.approx(0.75 * math.sqrt(2.0) + 0.125, abs=1e-12)


def test_alpha_outside_zero_to_one_is_refused():
    with pytest.raises(ValueError):
        calculate_mixed_edge_costs(build_square_grid([40.0, 50.0, 60.0, 80.0]), alpha=1.5)


def build_published_graph(number_of_rows: int, number_of_columns: int, seed: int) -> nx.Graph:
    """Nodes as the published builder stores them; edges added by the published builder itself."""
    generator = random.Random(seed)
    graph = nx.Graph()
    for row in range(number_of_rows):
        for column in range(number_of_columns):
            if generator.random() < 0.1:
                continue
            graph.add_node(
                (row, column), noise=generator.choice([40.0, 47.5, 52.5, 57.5, 62.5, 67.5, 77.5]),
                easting=530_000.0 + 100.0 * column + generator.uniform(-1e-7, 1e-7),
                northing=178_000.0 + 100.0 * row + generator.uniform(-1e-7, 1e-7),
            )
    _connect_adjacent_cells(graph)
    return graph


@pytest.mark.parametrize("alpha", [0.25, 0.5, 0.75, 1.0])
def test_grid_read_from_a_published_graph_has_its_edges_and_published_costs(alpha):
    """Characterisation: every edge of the graph, with exactly the cost of the published weight function."""
    graph = build_published_graph(number_of_rows=12, number_of_columns=15, seed=3)
    published_weight = make_mixed_distance_noise_weight(graph, alpha, higher_noise_is_better=False)
    nodes = sorted(graph.nodes)

    grid = read_navigation_grid_from_graph(graph, CELL_SIZE_M)
    costs = calculate_mixed_edge_costs(grid, alpha)

    edges = [(nodes[start], nodes[end]) for start, end in zip(grid.edge_starts.tolist(), grid.edge_ends.tolist())]
    assert len(edges) == graph.number_of_edges() and all(graph.has_edge(*edge) for edge in edges)
    assert len({frozenset(edge) for edge in edges}) == len(edges)
    assert costs.tolist() == [published_weight(start, end, graph.edges[start, end]) for start, end in edges]
    assert grid.eastings.tolist() == [graph.nodes[node]["easting"] for node in nodes]
    assert grid.northings.tolist() == [graph.nodes[node]["northing"] for node in nodes]
