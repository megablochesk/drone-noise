"""The navigation grid as arrays: one node per cell, joined to its eight neighbours.

It holds what the published NetworkX graph holds (cell centre, cell level, edge length, mean level of the two
cells of an edge), so the cost of every edge is one array operation instead of a function call per edge.
"""
import math
from dataclasses import dataclass

import networkx as nx
import numpy as np

# Each pair of neighbours is listed once: east, north-west, north, north-east.
NEIGHBOUR_SHIFTS = ((0, 1), (1, -1), (1, 0), (1, 1))
NO_CELL = -1
RANGE_OF_EQUAL_LEVELS = 1.0


@dataclass(frozen=True)
class NavigationGrid:
    """Cells sorted by (row, column); every edge once, as positions in that order."""
    cell_size_m: float
    rows: np.ndarray
    columns: np.ndarray
    eastings: np.ndarray
    northings: np.ndarray
    noise_levels_db: np.ndarray
    edge_starts: np.ndarray
    edge_ends: np.ndarray
    edge_lengths_m: np.ndarray
    edge_noise_levels_db: np.ndarray


def index_cells(rows: np.ndarray, columns: np.ndarray) -> np.ndarray:
    """Position of each cell by [row, column]; NO_CELL where the grid has none."""
    positions = np.full((rows.max() + 1, columns.max() + 1), NO_CELL, dtype=np.int64)
    positions[rows, columns] = np.arange(len(rows))
    return positions


def find_neighbours(rows: np.ndarray, columns: np.ndarray, row_shift: int, column_shift: int) -> tuple[np.ndarray, np.ndarray]:
    """Positions of the cells that have a neighbour at the shift, and of those neighbours."""
    positions = index_cells(rows, columns)
    neighbour_rows, neighbour_columns = rows + row_shift, columns + column_shift
    inside = (neighbour_rows < positions.shape[0]) & (neighbour_columns >= 0) & (neighbour_columns < positions.shape[1])

    starts = np.flatnonzero(inside)
    ends = positions[neighbour_rows[starts], neighbour_columns[starts]]
    return starts[ends != NO_CELL], ends[ends != NO_CELL]


def connect_neighbouring_cells(
        rows: np.ndarray, columns: np.ndarray, cell_size_m: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Edge starts, ends and lengths; a diagonal is sqrt(2) cells long."""
    starts, ends, lengths_m = [], [], []
    for row_shift, column_shift in NEIGHBOUR_SHIFTS:
        shift_starts, shift_ends = find_neighbours(rows, columns, row_shift, column_shift)
        is_diagonal = row_shift != 0 and column_shift != 0
        starts.append(shift_starts)
        ends.append(shift_ends)
        lengths_m.append(np.full(len(shift_starts), cell_size_m * (math.sqrt(2.0) if is_diagonal else 1)))
    return np.concatenate(starts), np.concatenate(ends), np.concatenate(lengths_m)


def build_navigation_grid(
        rows: np.ndarray, columns: np.ndarray, eastings: np.ndarray, northings: np.ndarray,
        noise_levels_db: np.ndarray, cell_size_m: float,
) -> NavigationGrid:
    order = np.lexsort((columns, rows))
    rows, columns, noise_levels_db = rows[order], columns[order], noise_levels_db[order]
    edge_starts, edge_ends, edge_lengths_m = connect_neighbouring_cells(rows, columns, cell_size_m)
    return NavigationGrid(
        cell_size_m=cell_size_m, rows=rows, columns=columns, eastings=eastings[order], northings=northings[order],
        noise_levels_db=noise_levels_db, edge_starts=edge_starts, edge_ends=edge_ends, edge_lengths_m=edge_lengths_m,
        edge_noise_levels_db=(noise_levels_db[edge_starts] + noise_levels_db[edge_ends]) / 2,
    )


def read_navigation_grid_from_graph(graph: nx.Graph, cell_size_m: float) -> NavigationGrid:
    """The grid of a published navigation graph, whose nodes are (row, column) with a level and a centre."""
    nodes = sorted(graph.nodes)
    return build_navigation_grid(
        rows=np.array([row for row, _ in nodes], dtype=np.int64),
        columns=np.array([column for _, column in nodes], dtype=np.int64),
        eastings=np.array([graph.nodes[node]["easting"] for node in nodes], dtype=np.float64),
        northings=np.array([graph.nodes[node]["northing"] for node in nodes], dtype=np.float64),
        noise_levels_db=np.array([graph.nodes[node]["noise"] for node in nodes], dtype=np.float64),
        cell_size_m=cell_size_m,
    )


def normalise_edge_levels(grid: NavigationGrid) -> np.ndarray:
    """Edge levels on 0-1 over the range of the cell levels, as the published weight normalises them."""
    lowest_level_db = np.nanmin(grid.noise_levels_db)
    level_range_db = np.nanmax(grid.noise_levels_db) - lowest_level_db
    if not np.isfinite(level_range_db) or level_range_db <= 0.0:
        level_range_db = RANGE_OF_EQUAL_LEVELS
    return np.clip((grid.edge_noise_levels_db - lowest_level_db) / level_range_db, 0.0, 1.0)


def calculate_mixed_edge_costs(grid: NavigationGrid, alpha: float) -> np.ndarray:
    """(1 - alpha) x length in cells + alpha x normalised level: louder edges cost more.

    Costs that are not finite or are negative become zero, as the published weight function returns them.
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be in [0, 1]")

    costs = (1.0 - alpha) * (grid.edge_lengths_m / grid.cell_size_m) + alpha * normalise_edge_levels(grid)
    return np.where(np.isfinite(costs), np.maximum(costs, 0.0), 0.0)
