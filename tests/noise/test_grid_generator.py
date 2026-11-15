"""Which 500 m cells belong to the study area: characterisation of the published grid code.

A cell belongs to the grid if it intersects the boundary polygon; touching an edge or a corner counts.
"""
from pathlib import Path

import numpy as np
import pytest
import shapely
from shapely.geometry import MultiPolygon, Polygon, box

from census_analysis.msoa_data import load_msoa_data
from experiments.revision.result_store import ResultStore, load_stored_grid
from common.enum import BoundaryDatum
from common.file_utils import load_dataframe_from_pickle
from common.path_configs import CELL_POPULATION_PATH, PATH_CONFIGS
from noise.grid_generator import build_cell_matrix, filter_cells_in_polygon, get_valid_cells, load_study_boundary_polygon
from noise.noise_grid import load_noise_grid
from tests.legacy_reference import load_legacy_module

LEGACY_GRID_MODULE = load_legacy_module("noise/grid_generator.py")
CELL_SIZE_M = 10.0
CELLS_PER_SIDE = 4
# West, south, east, north edge of the boundary as the published model reads it (metres, British National Grid).
PUBLISHED_BOUNDARY_EXTENT_M = (503_677.80, 155_794.05, 562_074.46, 200_882.38)
EXTENT_ROUNDING_M = 0.01
# The MSOA polygons are drawn on the same coast and borough edges: the boundary must meet their extent within this.
CENSUS_EXTENT_TOLERANCE_M = 10.0
# The published reading sits about 110 m east and 55 m south of the census extent.
PUBLISHED_READING_SMALLEST_OFFSET_M = 50.0
FINE_CELL_SIZE_M = 100
# The 500 m grid stored with the published-design runs of the revision (results/artifacts/grids).
STORED_RESULTS_DIRECTORY = Path(__file__).resolve().parents[2] / "results" / "artifacts"
STORED_PUBLISHED_GRID_FINGERPRINT = "1ab3b518f3d05324"


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


def cells_of_stored_published_grid() -> list[tuple[int, int, float, float]]:
    grid = load_stored_grid(ResultStore(STORED_RESULTS_DIRECTORY), STORED_PUBLISHED_GRID_FINGERPRINT)
    return list(zip(
        grid.rows.tolist(), grid.columns.tolist(), grid.centroid_northings.tolist(), grid.centroid_eastings.tolist()
    ))


def cells_with_centroids(cells) -> list[tuple[int, int, float, float]]:
    return [(cell.row, cell.column, cell.centroid.northing, cell.centroid.easting) for cell in cells]


def test_study_grid_matches_the_stored_published_grid_cell_by_cell():
    """Same cells, order and centroids as the stored grid, which the slow test below ties to the published code."""
    assert cells_with_centroids(build_cell_matrix()) == cells_of_stored_published_grid()


@pytest.mark.slow
def test_study_grid_matches_the_published_grid_cell_by_cell():
    current, legacy = build_cell_matrix(), LEGACY_GRID_MODULE.build_cell_matrix()
    assert [(cell.row, cell.column, cell.centroid) for cell in current] == \
           [(cell.row, cell.column, cell.centroid) for cell in legacy]


def offsets_from_census_extent_m(boundary) -> np.ndarray:
    census_extent = shapely.total_bounds(np.array(list(load_msoa_data().msoa_index.values()), dtype=object))
    return np.array(boundary.bounds) - census_extent


def test_the_published_reading_keeps_the_boundary_where_the_published_model_has_it():
    """The default reading is the published code's: the file's coordinates taken as WGS84."""
    boundary = load_study_boundary_polygon(BoundaryDatum.WGS84)
    published_reading = LEGACY_GRID_MODULE.load_and_reproject_geojson(PATH_CONFIGS.london_boundaries_path)

    assert boundary.bounds == tuple(published_reading.total_bounds)
    assert boundary.bounds == pytest.approx(PUBLISHED_BOUNDARY_EXTENT_M, abs=EXTENT_ROUNDING_M)
    assert np.abs(offsets_from_census_extent_m(boundary)).min() > PUBLISHED_READING_SMALLEST_OFFSET_M


def test_reading_the_boundary_on_osgb36_puts_it_on_the_census_extent():
    """Independent data: every edge of the OSGB36 reading lies within a few metres of the MSOA polygons' edge."""
    offsets_m = offsets_from_census_extent_m(load_study_boundary_polygon(BoundaryDatum.OSGB36))
    assert np.abs(offsets_m).max() < CENSUS_EXTENT_TOLERANCE_M


def test_the_published_grid_is_the_grid_of_the_published_reading():
    published_grid = load_noise_grid()
    assert load_noise_grid(500, BoundaryDatum.WGS84) is published_grid
    assert [(cell["row"], cell["col"]) for cell in get_valid_cells(500, BoundaryDatum.WGS84)] == \
           list(zip(published_grid.rows.tolist(), published_grid.columns.tolist()))


def test_the_osgb36_reading_moves_cells_in_the_west_and_out_of_the_south():
    """The OSGB36 boundary lies about 110 m west and 55 m north of the published one, on the same cell origin:
    at 100 m the westmost column gains cells and the southmost row loses them."""
    published, osgb36 = load_noise_grid(FINE_CELL_SIZE_M), load_noise_grid(FINE_CELL_SIZE_M, BoundaryDatum.OSGB36)

    assert np.count_nonzero(osgb36.columns == 0) > np.count_nonzero(published.columns == 0)
    assert np.count_nonzero(osgb36.rows == 0) < np.count_nonzero(published.rows == 0)
    published_centroids, osgb36_centroids = centroids_by_cell(published), centroids_by_cell(osgb36)
    shared_cells = published_centroids.keys() & osgb36_centroids.keys()
    assert all(published_centroids[cell] == osgb36_centroids[cell] for cell in shared_cells)


def centroids_by_cell(grid) -> dict[tuple[int, int], tuple[float, float]]:
    cells = zip(grid.rows.tolist(), grid.columns.tolist())
    return dict(zip(cells, zip(grid.centroid_eastings.tolist(), grid.centroid_northings.tolist())))
