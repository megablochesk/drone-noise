"""Running the model on a finer noise grid. 500 m stays the default everywhere; a run at 100 m flies the same
drones and hears them on 25 times as many cells."""
from dataclasses import dataclass, replace

import numpy as np
import pytest

from common.coordinate import Coordinate
from common.enum import BaselineNoiseMap, NoiseCalculation, OrderDatasetType
from common.model_configs import model_config
from common.path_configs import BASE_NOISE_PATH, PATH_CONFIGS, ROUND4_BASE_NOISE_PATH
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from experiments.revision.result_store import ResultStore, load_drone_levels
from experiments.revision.run_executor import destination_pool_path, execute_run
from experiments.revision.run_specification import RunSpecification, build_model_config, build_run_key
from metrics.cell_table import load_cell_table
from metrics.exposure_metrics import calculate_mean_noise_increase_db
from noise.energy_noise_tracker import EnergyNoiseTracker
from noise.noise_data_processor import find_base_noise_path, load_base_noise_data
from noise.noise_grid import load_noise_grid
from orders.msoa_zones import load_population_zones
from orders.seeded_order_pool import generate_destinations, save_destination_pool
from simulation.noise_monitor import NoiseMonitor

GIT_HASH = "0" * 40
FINE_CELL_SIZE_M = 100
FINE_CELLS_PER_PUBLISHED_CELL_SIDE = 5
FINE_GRID_ROWS, FINE_GRID_COLUMNS = 450, 583
SMALL_RUN = RunSpecification(
    stocking=OrderDatasetType.CLOSEST, number_of_drones=14, terminal_phases=False, seed=1, pool_size=60
)
FINE_MODEL = replace(model_config, grid=replace(model_config.grid, noise_cell_m=FINE_CELL_SIZE_M))


@dataclass
class DroneStub:
    current_location: Coordinate
    current_altitude: float


@pytest.fixture(scope="module")
def store(tmp_path_factory) -> ResultStore:
    result_store = ResultStore(tmp_path_factory.mktemp("artifacts"))
    pool_path = destination_pool_path(result_store, SMALL_RUN)
    pool_path.parent.mkdir(parents=True)
    save_destination_pool(generate_destinations(1, 60, load_population_zones()), pool_path)
    return result_store


def average_over_published_cells(fine_levels, to_averaged_quantity, from_averaged_quantity):
    parents = fine_levels.assign(
        row=fine_levels["row"] // FINE_CELLS_PER_PUBLISHED_CELL_SIDE,
        col=fine_levels["col"] // FINE_CELLS_PER_PUBLISHED_CELL_SIDE,
        quantity=to_averaged_quantity(fine_levels["noise_level"]),
    ).groupby(["row", "col"], as_index=False)["quantity"].mean()
    return parents.assign(noise_level=from_averaged_quantity(parents["quantity"]))


def test_specification_defaults_to_the_published_cell_size():
    assert SMALL_RUN.noise_cell_m == 500
    assert build_model_config(SMALL_RUN).grid.noise_cell_m == 500
    fine_run = replace(SMALL_RUN, noise_cell_m=FINE_CELL_SIZE_M)
    assert build_model_config(fine_run).grid.noise_cell_m == FINE_CELL_SIZE_M
    assert build_run_key(fine_run) != build_run_key(SMALL_RUN)


def test_each_map_has_one_file_per_cell_size():
    assert find_base_noise_path(BaselineNoiseMap.PUBLISHED, 500) == BASE_NOISE_PATH
    assert find_base_noise_path(BaselineNoiseMap.ROUND_4_ROAD, 500) == ROUND4_BASE_NOISE_PATH
    assert find_base_noise_path(BaselineNoiseMap.ROUND_4_ROAD, 100) == PATH_CONFIGS.round4_base_noise_path(100)
    assert find_base_noise_path(BaselineNoiseMap.ROUND_4_ROAD_ENERGY, 100) == PATH_CONFIGS.round4_energy_base_noise_path(100)
    assert len({find_base_noise_path(noise_map, size) for noise_map in BaselineNoiseMap for size in (100, 500)}) == 6


def test_fine_round_four_baseline_averages_to_the_published_cell_size():
    """The arithmetic mean over a 500 m cell is the mean of its 25 fine means; likewise for mean energies."""
    for noise_map, to_quantity, from_quantity in [
        (BaselineNoiseMap.ROUND_4_ROAD, lambda levels: levels, lambda levels: levels),
        (BaselineNoiseMap.ROUND_4_ROAD_ENERGY, lambda levels: 10.0 ** (levels / 10.0), lambda energy: 10.0 * np.log10(energy)),
    ]:
        fine, coarse = load_base_noise_data(noise_map, FINE_CELL_SIZE_M), load_base_noise_data(noise_map, 500)
        assert len(fine) == FINE_GRID_ROWS * FINE_GRID_COLUMNS
        averaged = average_over_published_cells(fine, to_quantity, from_quantity)
        merged = coarse.merge(averaged, on=["row", "col"], suffixes=("_coarse", "_fine"), validate="1:1")
        assert len(merged) == len(coarse) == 90 * 116
        np.testing.assert_allclose(merged["noise_level_fine"], merged["noise_level_coarse"], rtol=1e-9)


def test_energy_mean_is_never_below_the_arithmetic_mean():
    """Jensen's inequality, cell by cell."""
    arithmetic = load_base_noise_data(BaselineNoiseMap.ROUND_4_ROAD, FINE_CELL_SIZE_M)
    energy = load_base_noise_data(BaselineNoiseMap.ROUND_4_ROAD_ENERGY, FINE_CELL_SIZE_M)
    assert (energy["noise_level"] >= arithmetic["noise_level"] - 1e-9).all()
    assert energy["noise_level"].mean() > arithmetic["noise_level"].mean()


def test_fine_cell_table_is_aligned_with_the_fine_grid():
    grid, table = load_noise_grid(FINE_CELL_SIZE_M), load_cell_table(BaselineNoiseMap.ROUND_4_ROAD, FINE_CELL_SIZE_M)
    np.testing.assert_array_equal(table.rows, grid.rows)
    np.testing.assert_array_equal(table.columns, grid.columns)
    assert len(table.population) == len(table.baseline_levels_db) == len(grid.rows)
    assert table.baseline_levels_db.min() >= 40.0
    assert load_cell_table() is load_cell_table(BaselineNoiseMap.PUBLISHED, 500)


def test_drone_hovering_over_a_fine_cell_centroid_gives_fifty_decibels_there():
    """Hand calculation: 90 dB source held 100 m above the centroid for every step is 90 - 40 = 50 dB."""
    grid = load_noise_grid(FINE_CELL_SIZE_M)
    hover_location = Coordinate(grid.centroid_northings[1_000], grid.centroid_eastings[1_000])
    with use_simulation_config(SimulationConfig(noise_calculation=NoiseCalculation.ENERGY_SUM, model=FINE_MODEL)):
        tracker = EnergyNoiseTracker()
    for _ in range(3):
        tracker.track_drones([DroneStub(hover_location, 100.0)])

    levels = tracker.calculate_drone_noise_levels()
    assert len(levels) == len(grid.rows)
    assert levels[1_000] == pytest.approx(50.0, abs=1e-9)


def test_fine_cells_are_rejected_by_the_per_step_calculation():
    """The published per-step path is tied to the published grid."""
    with use_simulation_config(SimulationConfig(model=FINE_MODEL)):
        with pytest.raises(ValueError, match="cell size"):
            NoiseMonitor()


def test_fine_run_flies_the_same_drones_and_reports_fine_metrics(store):
    coarse_row = execute_run(SMALL_RUN, store, GIT_HASH)
    fine_run = replace(SMALL_RUN, noise_cell_m=FINE_CELL_SIZE_M, baseline_noise_map=BaselineNoiseMap.ROUND_4_ROAD)
    fine_row = execute_run(fine_run, store, GIT_HASH)
    drone_levels_db = load_drone_levels(store, build_run_key(fine_run))
    cell_table = load_cell_table(BaselineNoiseMap.ROUND_4_ROAD, FINE_CELL_SIZE_M)

    assert fine_row["noise_cell_m"] == FINE_CELL_SIZE_M
    for unchanged in ["delivered_orders", "assigned_orders", "airborne_drone_seconds", "mean_trip_distance_m"]:
        assert fine_row[unchanged] == coarse_row[unchanged]
    assert len(drone_levels_db) == len(load_noise_grid(FINE_CELL_SIZE_M).rows)
    assert fine_row["mean_noise_increase_db"] == pytest.approx(
        calculate_mean_noise_increase_db(drone_levels_db, cell_table.baseline_levels_db), abs=1e-12
    )
