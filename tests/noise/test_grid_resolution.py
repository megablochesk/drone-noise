"""The noise grid at a chosen cell size. 500 m stays the default and the published grid; 100 m cells nest in it.

Bounding box of the model: 503,568.18-561,950.07 m east, 155,850.78-200,930.56 m north.
"""
import numpy as np
import pytest

from noise.grid_generator import compute_grid_dimensions
from noise.noise_grid import load_noise_grid

PUBLISHED_CELL_SIZE_M = 500
FINE_CELL_SIZE_M = 100
FINE_CELLS_PER_PUBLISHED_CELL_SIDE = 5
GREATER_LONDON_AREA_KM2 = 1_572.0
FINE_CELL_AREA_KM2 = 0.01


def test_grid_dimensions_follow_the_cell_size():
    """floor(45,079.78 / 500) = 90 rows and floor(58,381.89 / 500) = 116 columns; 450 and 583 at 100 m."""
    assert compute_grid_dimensions() == (90, 116)
    assert compute_grid_dimensions(PUBLISHED_CELL_SIZE_M) == (90, 116)
    assert compute_grid_dimensions(FINE_CELL_SIZE_M) == (450, 583)


def test_default_grid_is_the_five_hundred_metre_grid_and_is_built_once():
    assert load_noise_grid() is load_noise_grid(PUBLISHED_CELL_SIZE_M)
    assert len(load_noise_grid().rows) == 6_656


def test_fine_grid_centroid_is_the_middle_of_its_hundred_metre_cell():
    """Hand calculation for the cell of central London in row 245, column 264:
    155,850.78 + 245.5 * 100 = 180,400.78 N and 503,568.18 + 264.5 * 100 = 530,018.18 E."""
    grid = load_noise_grid(FINE_CELL_SIZE_M)
    cell = np.flatnonzero((grid.rows == 245) & (grid.columns == 264))[0]
    assert grid.centroid_northings[cell] == pytest.approx(180_400.78, abs=1e-6)
    assert grid.centroid_eastings[cell] == pytest.approx(530_018.18, abs=1e-6)


def test_fine_grid_covers_greater_london_and_little_else():
    """Cells that meet the boundary: at least the area of Greater London, and no more than 25 per published cell
    plus the 3-column strip (450 rows) that whole 500 m cells leave uncovered in the east."""
    number_of_fine_cells = len(load_noise_grid(FINE_CELL_SIZE_M).rows)
    assert number_of_fine_cells >= GREATER_LONDON_AREA_KM2 / FINE_CELL_AREA_KM2
    assert number_of_fine_cells <= 6_656 * FINE_CELLS_PER_PUBLISHED_CELL_SIDE ** 2 + 3 * 450
    assert len(set(zip(load_noise_grid(FINE_CELL_SIZE_M).rows.tolist(), load_noise_grid(FINE_CELL_SIZE_M).columns.tolist()))) == number_of_fine_cells


def test_fine_cells_lie_inside_cells_of_the_published_grid():
    """A 100 m cell that meets the boundary lies in a 500 m cell that meets it too (where the 500 m grid reaches)."""
    fine, published = load_noise_grid(FINE_CELL_SIZE_M), load_noise_grid()
    published_cells = set(zip(published.rows.tolist(), published.columns.tolist()))
    parent_rows = fine.rows // FINE_CELLS_PER_PUBLISHED_CELL_SIDE
    parent_columns = fine.columns // FINE_CELLS_PER_PUBLISHED_CELL_SIDE
    inside_published_extent = parent_columns < 116
    parents = set(zip(parent_rows[inside_published_extent].tolist(), parent_columns[inside_published_extent].tolist()))
    assert parents == published_cells
