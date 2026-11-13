import numpy as np
import pandas as pd
import pytest

from experiments.revision.result_store import (
    ResultStore,
    collect_rows,
    has_result,
    load_drone_levels,
    load_row,
    load_trip_distances,
    save_result,
    select_pending,
)

DRONE_LEVELS_DB = np.array([31.5, -np.inf, 48.25])
TRIP_DISTANCES_M = np.array([1_200.0, 8_100.5])
ROW = {"run_key": "abc", "delivered_orders": 2, "mean_noise_increase_db": 0.125}


def test_result_round_trip(tmp_path):
    """Invariant: what is saved is what is loaded."""
    store = ResultStore(tmp_path)
    assert not has_result(store, "abc")
    save_result(store, "abc", ROW, DRONE_LEVELS_DB, TRIP_DISTANCES_M)

    assert has_result(store, "abc")
    assert load_row(store, "abc") == ROW
    np.testing.assert_array_equal(load_drone_levels(store, "abc"), DRONE_LEVELS_DB)
    np.testing.assert_array_equal(load_trip_distances(store, "abc"), TRIP_DISTANCES_M)


def test_run_without_its_row_counts_as_missing(tmp_path):
    """The row is written last, so artefacts left by an interrupted run must not look like a finished one."""
    store = ResultStore(tmp_path)
    save_result(store, "abc", ROW, DRONE_LEVELS_DB, TRIP_DISTANCES_M)
    store.row_path("abc").unlink()
    assert not has_result(store, "abc")


def test_only_runs_without_a_result_are_pending(tmp_path):
    """Resumability: keys with a stored row are skipped, the others keep their order."""
    store = ResultStore(tmp_path)
    save_result(store, "done", ROW, DRONE_LEVELS_DB, TRIP_DISTANCES_M)
    assert select_pending(store, ["first", "done", "second"]) == ["first", "second"]


def test_rows_are_collected_in_the_requested_order(tmp_path):
    """Invariant: one table row per key, in key order."""
    store = ResultStore(tmp_path)
    for key, delivered in [("b", 5), ("a", 7)]:
        save_result(store, key, {"run_key": key, "delivered_orders": delivered}, DRONE_LEVELS_DB, TRIP_DISTANCES_M)
    table = collect_rows(store, ["a", "b"])
    pd.testing.assert_frame_equal(table, pd.DataFrame({"run_key": ["a", "b"], "delivered_orders": [7, 5]}))


def test_collecting_a_missing_result_fails(tmp_path):
    """A phase table must never silently drop a run."""
    with pytest.raises(FileNotFoundError):
        collect_rows(ResultStore(tmp_path), ["missing"])
