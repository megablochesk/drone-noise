"""A stored map is only meaningful on the grid it was computed on, so the store keeps that grid with the run."""
import numpy as np
import pandas as pd
import pytest

from experiments.revision.result_store import (
    ResultStore,
    calculate_grid_fingerprint,
    ensure_runs_are_on_grid,
    load_stored_grid,
    save_grid,
)
from noise.noise_grid import NoiseGrid

GRID = NoiseGrid(
    rows=np.array([0, 0, 1]), columns=np.array([0, 1, 0]),
    centroid_northings=np.array([50.0, 50.0, 150.0]), centroid_eastings=np.array([50.0, 150.0, 50.0]),
)
OTHER_GRID = NoiseGrid(
    rows=np.array([0, 0, 1]), columns=np.array([0, 1, 1]),
    centroid_northings=np.array([50.0, 50.0, 150.0]), centroid_eastings=np.array([50.0, 150.0, 150.0]),
)


def test_fingerprint_names_the_cells_and_their_order():
    reordered = NoiseGrid(GRID.rows[::-1], GRID.columns[::-1], GRID.centroid_northings[::-1], GRID.centroid_eastings[::-1])

    assert calculate_grid_fingerprint(GRID) == calculate_grid_fingerprint(GRID)
    assert calculate_grid_fingerprint(GRID) != calculate_grid_fingerprint(OTHER_GRID)
    assert calculate_grid_fingerprint(GRID) != calculate_grid_fingerprint(reordered)


def test_a_grid_is_stored_once_and_read_back(tmp_path):
    store = ResultStore(tmp_path)

    fingerprint = save_grid(store, GRID)
    first_written = store.grid_path(fingerprint).stat().st_mtime_ns
    assert save_grid(store, GRID) == fingerprint
    stored = load_stored_grid(store, fingerprint)

    assert store.grid_path(fingerprint).stat().st_mtime_ns == first_written
    np.testing.assert_array_equal(stored.rows, GRID.rows)
    np.testing.assert_array_equal(stored.columns, GRID.columns)
    np.testing.assert_array_equal(stored.centroid_eastings, GRID.centroid_eastings)
    np.testing.assert_array_equal(stored.centroid_northings, GRID.centroid_northings)


def test_runs_computed_on_another_grid_are_refused():
    runs = pd.DataFrame({"run_key": ["a", "b"], "grid_fingerprint": [calculate_grid_fingerprint(GRID)] * 2})

    ensure_runs_are_on_grid(runs, GRID)
    with pytest.raises(ValueError, match="another grid"):
        ensure_runs_are_on_grid(runs, OTHER_GRID)


def test_runs_without_a_recorded_grid_are_accepted():
    """A run table without the column, or with empty cells, makes no statement about its grid."""
    ensure_runs_are_on_grid(pd.DataFrame({"run_key": ["a"]}), GRID)
    ensure_runs_are_on_grid(pd.DataFrame({"run_key": ["a"], "grid_fingerprint": [np.nan]}), GRID)


def test_a_stored_run_without_a_grid_gets_the_grid_recorded(tmp_path):
    """The other fields of the row stay as they are; a run that names its grid is left alone."""
    from experiments.revision.result_store import load_row, record_grid_of_stored_run, save_result

    store = ResultStore(tmp_path)
    save_result(store, "run1", {"run_key": "run1", "delivered_orders": 7}, np.zeros(3), np.zeros(2))

    assert record_grid_of_stored_run(store, "run1", GRID) is True
    assert load_row(store, "run1") == {
        "run_key": "run1", "delivered_orders": 7, "grid_fingerprint": calculate_grid_fingerprint(GRID),
    }
    assert store.grid_path(calculate_grid_fingerprint(GRID)).exists()
    assert record_grid_of_stored_run(store, "run1", OTHER_GRID) is False
    assert load_row(store, "run1")["grid_fingerprint"] == calculate_grid_fingerprint(GRID)


def test_a_grid_of_another_size_than_the_map_is_refused(tmp_path):
    from experiments.revision.result_store import record_grid_of_stored_run, save_result

    store = ResultStore(tmp_path)
    save_result(store, "run1", {"run_key": "run1"}, np.zeros(5), np.zeros(2))

    with pytest.raises(ValueError, match="5 cells"):
        record_grid_of_stored_run(store, "run1", GRID)
