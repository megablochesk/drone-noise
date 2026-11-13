import numpy as np
import pytest

from noise.noise_grid import load_noise_grid

PUBLISHED_NUMBER_OF_CELLS = 6_656


def test_grid_has_the_cells_of_the_published_maps():
    """Published number: every saved result map and the population table have 6,656 cells."""
    grid = load_noise_grid()
    assert len(grid.rows) == len(grid.columns) == PUBLISHED_NUMBER_OF_CELLS
    assert len(set(zip(grid.rows.tolist(), grid.columns.tolist()))) == PUBLISHED_NUMBER_OF_CELLS


def test_centroid_is_the_middle_of_the_five_hundred_metre_cell():
    """Hand calculation for row 0, column 54: 155850.78 + 250 = 156100.78 N, 503568.18 + 54.5 * 500 = 530818.18 E."""
    grid = load_noise_grid()
    cell = np.flatnonzero((grid.rows == 0) & (grid.columns == 54))[0]
    assert grid.centroid_northings[cell] == pytest.approx(156_100.78, abs=1e-6)
    assert grid.centroid_eastings[cell] == pytest.approx(530_818.18, abs=1e-6)
