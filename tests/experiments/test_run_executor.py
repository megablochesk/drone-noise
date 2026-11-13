"""One tiny seeded run through the whole executor: real grid, real census zones, 60 orders."""
import numpy as np
import pytest

from common.enum import OrderDatasetType
from experiments.revision.result_store import ResultStore, load_drone_levels, load_row, load_trip_distances
from experiments.revision.run_executor import destination_pool_path, execute_run
from experiments.revision.run_specification import RunSpecification, build_run_key
from metrics.cell_table import load_cell_table
from metrics.exposure_metrics import calculate_mean_noise_increase_db, calculate_newly_exposed_population
from orders.msoa_zones import load_population_zones
from orders.seeded_order_pool import generate_destinations, save_destination_pool

GIT_HASH = "0" * 40
SPECIFICATION = RunSpecification(
    stocking=OrderDatasetType.CLOSEST, number_of_drones=14, terminal_phases=False, seed=1, pool_size=60
)


@pytest.fixture(scope="module")
def store(tmp_path_factory) -> ResultStore:
    result_store = ResultStore(tmp_path_factory.mktemp("artifacts"))
    pool_path = destination_pool_path(result_store, SPECIFICATION)
    pool_path.parent.mkdir(parents=True)
    save_destination_pool(generate_destinations(1, 60, load_population_zones()), pool_path)
    return result_store


@pytest.fixture(scope="module")
def row(store) -> dict:
    return execute_run(SPECIFICATION, store, GIT_HASH)


def test_row_identifies_the_run(row):
    """Every row carries its key, the full configuration, the commit and the wall time."""
    assert row["run_key"] == build_run_key(SPECIFICATION)
    assert row["git_hash"] == GIT_HASH
    assert (row["stocking"], row["number_of_drones"], row["seed"], row["pool_size"]) == ("closest", 14, 1, 60)
    assert row["wall_time_s"] > 0


def test_order_bookkeeping_is_consistent(row):
    """Invariant: every order is delivered, still in the air, or left at its warehouse."""
    assert row["delivered_orders"] <= row["assigned_orders"] <= 60
    assert row["assigned_orders"] - row["delivered_orders"] <= 14
    assert row["orders_left"] == 60 - row["assigned_orders"]
    assert sum(warehouse["drones"] for warehouse in row["per_warehouse"].values()) == 14


def test_stored_row_and_artefacts_match_the_returned_row(store, row):
    """Invariant: what the executor returns is what it stored."""
    run_key = build_run_key(SPECIFICATION)
    assert load_row(store, run_key) == row
    assert len(load_trip_distances(store, run_key)) == row["assigned_orders"]
    assert len(load_drone_levels(store, run_key)) == len(load_cell_table().population)


def test_row_metrics_can_be_recomputed_from_the_stored_map(store, row):
    """Cross-check: the headline metrics follow from the saved drone-only map and the cell table."""
    drone_levels_db = load_drone_levels(store, build_run_key(SPECIFICATION))
    cell_table = load_cell_table()
    assert row["mean_noise_increase_db"] == pytest.approx(
        calculate_mean_noise_increase_db(drone_levels_db, cell_table.baseline_levels_db), abs=1e-12
    )
    assert row["newly_exposed_population_55db"] == pytest.approx(
        calculate_newly_exposed_population(drone_levels_db, cell_table.baseline_levels_db, cell_table.population, 55.0)
    )
    assert row["mean_noise_increase_db"] > 0


def test_same_specification_gives_the_same_result(store, row):
    """Invariant: a run is a deterministic function of its specification."""
    repeated = execute_run(SPECIFICATION, store, GIT_HASH)
    for metric in ["delivered_orders", "mean_noise_increase_db", "newly_exposed_population_55db", "airborne_drone_seconds"]:
        assert repeated[metric] == row[metric]
    np.testing.assert_array_equal(
        load_drone_levels(store, build_run_key(SPECIFICATION)), load_drone_levels(store, repeated["run_key"])
    )
