import numpy as np
import pytest

from census_analysis.msoa_data import load_msoa_data
from metrics.cell_table import load_cell_table
from noise.noise_grid import load_noise_grid

UNCOVERED_POPULATION_SHARE_LIMIT = 1e-4


def test_cell_table_is_aligned_with_the_noise_grid():
    """Invariant: the table lists exactly the grid cells, in grid order."""
    table, grid = load_cell_table(), load_noise_grid()
    np.testing.assert_array_equal(table.rows, grid.rows)
    np.testing.assert_array_equal(table.columns, grid.columns)
    assert len(table.population) == len(table.baseline_levels_db) == len(grid.rows)


def test_gridded_population_sums_to_the_input_population_total():
    """Invariant: area-weighted gridding moves people between cells but creates or removes none.

    The grid is cut to whole 500 m cells (90 rows x 116 columns), leaving an 80 m strip in the north and a
    382 m strip in the east of the bounding box uncovered, so the gridded total may fall short of the MSOA
    total by the few people living there, never exceed it.
    """
    input_total = sum(load_msoa_data().msoa_populations.values())
    gridded_total = load_cell_table().population.sum()
    assert gridded_total <= input_total
    assert (input_total - gridded_total) / input_total < UNCOVERED_POPULATION_SHARE_LIMIT


def test_baseline_levels_are_the_published_baseline():
    """Published file facts (Phase 0): the minimum level is the 40 dB fill value and no cell is below it."""
    baseline = load_cell_table().baseline_levels_db
    assert baseline.min() == pytest.approx(40.0)
    assert np.isfinite(baseline).all()
