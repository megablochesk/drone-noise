"""Which 500 m cells belong to the study area: characterisation of the published grid code.

A cell belongs to the grid if it intersects the boundary polygon; touching an edge or a corner counts.
"""
import pytest
from shapely.geometry import MultiPolygon, Polygon, box

from common.file_utils import load_dataframe_from_pickle
from common.path_configs import CELL_POPULATION_PATH
from noise.grid_generator import build_cell_matrix, filter_cells_in_polygon
from noise.noise_grid import load_noise_grid
from tests.legacy_reference import load_legacy_module

LEGACY_GRID_MODULE = load_legacy_module("noise/grid_generator.py")
CELL_SIZE_M = 10.0
CELLS_PER_SIDE = 4


def build_square_cells() -> list[dict]:
    return [
        {
            "geometry": box(column * CELL_SIZE_M, row * CELL_SIZE_M, (column + 1) * CELL_SIZE_M, (row + 1) * CELL_SIZE_M),
            "row": row, "col": column,
        }
        for row in range(CELLS_PER_SIDE) for column in range(CELLS_PER_SIDE)
    ]


def kept_cells(cells: list[dict]) -> set[tuple[int, int]]:
    return {(cell["row"], cell["col"]) for cell in cells}


def test_cells_touching_the_boundary_at_an_edge_or_corner_are_kept():
    """Hand-built case: the boundary is exactly cell (1, 1); its eight neighbours touch it and are kept too."""
    boundary = box(10.0, 10.0, 20.0, 20.0)
    kept = kept_cells(filter_cells_in_polygon(build_square_cells(), boundary))
    assert kept == {(row, column) for row in range(3) for column in range(3)}


def test_cell_inside_a_hole_of_the_boundary_is_dropped():
    """Hand-built case: a hole from 9 m to 21 m swallows cell (1, 1) only."""
    boundary = Polygon(
        [(0.0, 0.0), (40.0, 0.0), (40.0, 40.0), (0.0, 40.0)],
        holes=[[(9.0, 9.0), (21.0, 9.0), (21.0, 21.0), (9.0, 21.0)]],
    )
    kept = kept_cells(filter_cells_in_polygon(build_square_cells(), boundary))
    assert kept == {(row, column) for row in range(4) for column in range(4)} - {(1, 1)}


BOUNDARIES = [
    box(10.0, 10.0, 20.0, 20.0),
    Polygon([(1.0, 1.0), (38.0, 3.0), (5.0, 37.0)]),
    Polygon([(0.0, 0.0), (40.0, 0.0), (40.0, 40.0), (0.0, 40.0)], holes=[[(9.0, 9.0), (21.0, 9.0), (21.0, 21.0), (9.0, 21.0)]]),
    MultiPolygon([box(2.0, 2.0, 4.0, 4.0), box(31.0, 31.0, 33.0, 33.0)]),
    box(50.0, 50.0, 60.0, 60.0),
]


@pytest.mark.parametrize("boundary", BOUNDARIES, ids=["one cell", "triangle", "hole", "two islands", "outside"])
def test_kept_cells_match_the_published_filter(boundary):
    current = filter_cells_in_polygon(build_square_cells(), boundary)
    legacy = LEGACY_GRID_MODULE.filter_cells_in_polygon(build_square_cells(), boundary)
    assert [(cell["row"], cell["col"]) for cell in current] == [(cell["row"], cell["col"]) for cell in legacy]


def test_grid_cells_are_the_cells_of_the_published_population_table():
    """Independent data: the population table was computed for the published grid, cell by cell."""
    population_cells = load_dataframe_from_pickle(CELL_POPULATION_PATH)
    grid = load_noise_grid()
    assert set(zip(grid.rows.tolist(), grid.columns.tolist())) == \
           set(zip(population_cells["row"].tolist(), population_cells["col"].tolist()))


@pytest.mark.slow
def test_study_grid_matches_the_published_grid_cell_by_cell():
    current, legacy = build_cell_matrix(), LEGACY_GRID_MODULE.build_cell_matrix()
    assert [(cell.row, cell.column, cell.centroid) for cell in current] == \
           [(cell.row, cell.column, cell.centroid) for cell in legacy]
