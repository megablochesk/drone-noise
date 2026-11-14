"""Choosing the baseline noise map of a run. The published map stays the default everywhere, so existing
results and run keys are untouched; the Round 4 map changes only what is compared with the drone noise."""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from common.enum import BaselineNoiseMap, NoiseCalculation, OrderDatasetType
from common.path_configs import BASE_NOISE_PATH, ROUND4_BASE_NOISE_PATH
from common.simulation_configs import SimulationConfig
from experiments.revision.result_store import ResultStore, load_drone_levels
from experiments.revision.run_executor import destination_pool_path, execute_run
from experiments.revision.run_specification import RunSpecification, build_run_key, build_simulation_config
from metrics.cell_table import load_cell_table
from metrics.exposure_metrics import calculate_mean_noise_increase_db, calculate_newly_exposed_population
from noise.noise_data_processor import find_base_noise_path, load_base_noise_data, read_base_noise_data
from orders.msoa_zones import load_population_zones
from orders.seeded_order_pool import generate_destinations, save_destination_pool
from tests.simulation.simulation_helpers import (
    destination_east_of_warehouse,
    model_with_duration,
    run_small_simulation,
    write_order_dataset,
)

GIT_HASH = "0" * 40
STORED_RUN_KEY = "af17b589ffe4e1c8"
STORED_RUN = RunSpecification(
    stocking=OrderDatasetType.CLOSEST, number_of_drones=1250, terminal_phases=True, seed=1, pool_size=650_000
)
SMALL_RUN = RunSpecification(
    stocking=OrderDatasetType.CLOSEST, number_of_drones=14, terminal_phases=False, seed=1, pool_size=60
)
ROUND4_REPORTING_FLOOR_DB = 40.0
ROUND4_HIGHEST_PIXEL_LEVEL_DB = 90.0


@pytest.fixture(scope="module")
def store(tmp_path_factory) -> ResultStore:
    result_store = ResultStore(tmp_path_factory.mktemp("artifacts"))
    pool_path = destination_pool_path(result_store, SMALL_RUN)
    pool_path.parent.mkdir(parents=True)
    save_destination_pool(generate_destinations(1, 60, load_population_zones()), pool_path)
    return result_store


def test_published_map_is_the_default_and_keeps_the_keys_of_stored_runs():
    """af17b589ffe4e1c8 is the key under which this run was stored before the baseline could be chosen."""
    assert STORED_RUN.baseline_noise_map is BaselineNoiseMap.PUBLISHED
    assert build_run_key(STORED_RUN) == STORED_RUN_KEY
    assert build_run_key(replace(STORED_RUN, baseline_noise_map=BaselineNoiseMap.ROUND_4_ROAD)) != STORED_RUN_KEY


def test_each_map_has_its_own_file():
    assert find_base_noise_path(BaselineNoiseMap.PUBLISHED) == BASE_NOISE_PATH
    assert find_base_noise_path(BaselineNoiseMap.ROUND_4_ROAD) == ROUND4_BASE_NOISE_PATH


def test_default_baseline_is_the_published_map():
    pd.testing.assert_frame_equal(load_base_noise_data(), read_base_noise_data(BASE_NOISE_PATH))
    assert load_base_noise_data() is load_base_noise_data(BaselineNoiseMap.PUBLISHED)


def test_round_four_baseline_covers_the_same_cells_within_the_range_of_the_map():
    published, round4 = load_base_noise_data(), load_base_noise_data(BaselineNoiseMap.ROUND_4_ROAD)
    assert round4[["row", "col"]].equals(published[["row", "col"]])
    assert round4["noise_level"].min() >= ROUND4_REPORTING_FLOOR_DB
    assert round4["noise_level"].max() < ROUND4_HIGHEST_PIXEL_LEVEL_DB
    assert not round4["noise_level"].equals(published["noise_level"])


def test_cell_table_takes_its_baseline_from_the_chosen_map_and_nothing_else():
    published, round4 = load_cell_table(), load_cell_table(BaselineNoiseMap.ROUND_4_ROAD)
    np.testing.assert_array_equal(round4.rows, published.rows)
    np.testing.assert_array_equal(round4.columns, published.columns)
    np.testing.assert_array_equal(round4.population, published.population)
    assert not np.array_equal(round4.baseline_levels_db, published.baseline_levels_db)
    assert load_cell_table() is load_cell_table(BaselineNoiseMap.PUBLISHED)


def test_simulation_configuration_carries_the_chosen_map():
    assert SimulationConfig().baseline_noise_map is BaselineNoiseMap.PUBLISHED
    config = build_simulation_config(
        replace(SMALL_RUN, baseline_noise_map=BaselineNoiseMap.ROUND_4_ROAD), order_dataset_path="orders.csv",
        orders_to_process=60,
    )
    assert config.baseline_noise_map is BaselineNoiseMap.ROUND_4_ROAD


def test_simulated_impact_is_measured_against_the_chosen_map(tmp_path):
    orders_path = write_order_dataset(tmp_path / "orders.csv", [destination_east_of_warehouse(9_000.0)] * 20)
    config = SimulationConfig(
        order_dataset_path=orders_path, orders_to_process=20, number_of_drones=1, print_model_stats=False,
        noise_calculation=NoiseCalculation.ENERGY_SUM, model=model_with_duration(3_600),
        baseline_noise_map=BaselineNoiseMap.ROUND_4_ROAD,
    )
    impact = run_small_simulation(config).noise_monitor.impact
    round4 = load_base_noise_data(BaselineNoiseMap.ROUND_4_ROAD)
    merged = impact.merge(round4, on=["row", "col"], suffixes=("", "_round4"))
    assert len(merged) == len(impact) > 0
    assert merged["noise_level"].equals(merged["noise_level_round4"])


def test_run_against_round_four_flies_the_same_drones_and_reports_round_four_metrics(store):
    published_row = execute_run(SMALL_RUN, store, GIT_HASH)
    round4_run = replace(SMALL_RUN, baseline_noise_map=BaselineNoiseMap.ROUND_4_ROAD)
    round4_row = execute_run(round4_run, store, GIT_HASH)
    drone_levels_db = load_drone_levels(store, build_run_key(round4_run))
    cell_table = load_cell_table(BaselineNoiseMap.ROUND_4_ROAD)

    assert round4_row["baseline_noise_map"] == "round4_road_laeq16h" and published_row["baseline_noise_map"] == "published"
    for unchanged in ["delivered_orders", "assigned_orders", "airborne_drone_seconds", "mean_trip_distance_m"]:
        assert round4_row[unchanged] == published_row[unchanged]
    np.testing.assert_array_equal(drone_levels_db, load_drone_levels(store, build_run_key(SMALL_RUN)))
    assert round4_row["mean_noise_increase_db"] == pytest.approx(
        calculate_mean_noise_increase_db(drone_levels_db, cell_table.baseline_levels_db), abs=1e-12
    )
    assert round4_row["newly_exposed_population_55db"] == pytest.approx(
        calculate_newly_exposed_population(drone_levels_db, cell_table.baseline_levels_db, cell_table.population, 55.0)
    )
    assert round4_row["mean_noise_increase_db"] != published_row["mean_noise_increase_db"]
