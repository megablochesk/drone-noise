"""A run that reads the study boundary on OSGB36 computes, stores and scores its map on the grid of that reading,
with census tables of its own; the published reading keeps its files and grid."""
from dataclasses import replace

import numpy as np
import pytest

from census_analysis.cell_datasets import load_cell_age, load_cell_ethnicity, load_cell_population
from census_analysis.msoa_data import load_msoa_data
from common.enum import BaselineNoiseMap, BoundaryDatum, OrderDatasetType
from common.model_configs import model_config
from common.path_configs import PATH_CONFIGS
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from experiments.revision.result_store import (
    GRID_FINGERPRINT_COLUMN,
    ResultStore,
    calculate_grid_fingerprint,
    load_drone_levels,
    load_stored_grid,
)
from experiments.revision.run_executor import destination_pool_path, execute_run
from experiments.revision.run_specification import RunSpecification, build_run_key
from metrics.cell_table import load_cell_table
from noise.energy_noise_tracker import EnergyNoiseTracker
from noise.noise_grid import load_noise_grid
from orders.msoa_zones import load_population_zones
from orders.seeded_order_pool import generate_destinations, save_destination_pool
from simulation.noise_monitor import NoiseMonitor

GIT_HASH = "0" * 40
FINE_CELL_SIZE_M = 100
POOL_SIZE = 60
OSGB36_RUN = RunSpecification(
    stocking=OrderDatasetType.CLOSEST, number_of_drones=14, terminal_phases=False, seed=1, pool_size=POOL_SIZE,
    noise_cell_m=FINE_CELL_SIZE_M, baseline_noise_map=BaselineNoiseMap.ROUND_4_ROAD, boundary_datum=BoundaryDatum.OSGB36,
)
CELL_FILE_PATH_BUILDERS = (
    PATH_CONFIGS.cell_population_path, PATH_CONFIGS.cell_age_path, PATH_CONFIGS.cell_ethnicity_path,
)
OSGB36_MODEL = replace(model_config, grid=replace(model_config.grid, boundary_datum=BoundaryDatum.OSGB36))


def cells_of(table) -> list[tuple[int, int]]:
    return list(zip(table["row"].tolist(), table["col"].tolist()))


def grid_cells(grid) -> list[tuple[int, int]]:
    return list(zip(grid.rows.tolist(), grid.columns.tolist()))


def test_the_published_reading_keeps_the_names_of_its_cell_files():
    assert PATH_CONFIGS.cell_population_path(FINE_CELL_SIZE_M) == "recourses/data/cell_population_100.pkl"
    for build_path in CELL_FILE_PATH_BUILDERS:
        assert build_path(FINE_CELL_SIZE_M, BoundaryDatum.WGS84) == build_path(FINE_CELL_SIZE_M)
        assert build_path(500, BoundaryDatum.WGS84) == build_path(500)


def test_each_boundary_reading_has_its_own_cell_files():
    assert PATH_CONFIGS.cell_population_path(FINE_CELL_SIZE_M, BoundaryDatum.OSGB36) == \
           "recourses/data/cell_population_100_osgb36.pkl"
    paths = {
        build_path(size, datum) for build_path in CELL_FILE_PATH_BUILDERS for size in (100, 500) for datum in BoundaryDatum
    }
    assert len(paths) == len(CELL_FILE_PATH_BUILDERS) * 2 * len(BoundaryDatum)


def test_census_tables_of_the_osgb36_reading_list_the_cells_of_its_grid():
    grid = load_noise_grid(FINE_CELL_SIZE_M, BoundaryDatum.OSGB36)
    for load_table in (load_cell_population, load_cell_age, load_cell_ethnicity):
        assert sorted(cells_of(load_table(FINE_CELL_SIZE_M, BoundaryDatum.OSGB36))) == sorted(grid_cells(grid))


def test_the_osgb36_grid_holds_at_least_the_population_of_the_published_one():
    """The OSGB36 boundary follows the census edges, so its cells lose no residents to the outside of the census
    extent; both totals stay at or below the MSOA total."""
    input_total = sum(load_msoa_data().msoa_populations.values())
    published_total = load_cell_population(FINE_CELL_SIZE_M)["population"].sum()
    osgb36_total = load_cell_population(FINE_CELL_SIZE_M, BoundaryDatum.OSGB36)["population"].sum()
    assert published_total <= osgb36_total <= input_total * (1 + 1e-12)


def test_cell_table_of_the_osgb36_reading_is_aligned_with_its_grid():
    grid = load_noise_grid(FINE_CELL_SIZE_M, BoundaryDatum.OSGB36)
    table = load_cell_table(BaselineNoiseMap.ROUND_4_ROAD, FINE_CELL_SIZE_M, BoundaryDatum.OSGB36)
    np.testing.assert_array_equal(table.rows, grid.rows)
    np.testing.assert_array_equal(table.columns, grid.columns)
    assert len(table.population) == len(table.baseline_levels_db) == len(grid.rows)
    assert load_cell_table(BaselineNoiseMap.ROUND_4_ROAD, FINE_CELL_SIZE_M, BoundaryDatum.WGS84) is \
           load_cell_table(BaselineNoiseMap.ROUND_4_ROAD, FINE_CELL_SIZE_M)


def test_the_energy_tracker_hears_drones_on_the_grid_of_the_configured_reading():
    with use_simulation_config(SimulationConfig(model=OSGB36_MODEL)):
        tracker = EnergyNoiseTracker()
    assert tracker.grid is load_noise_grid(model_config.grid.noise_cell_m, BoundaryDatum.OSGB36)


def test_the_per_step_calculation_refuses_another_boundary_reading():
    """The published per-step path is tied to the published grid."""
    with use_simulation_config(SimulationConfig(model=OSGB36_MODEL)):
        with pytest.raises(ValueError, match="boundary"):
            NoiseMonitor()


@pytest.fixture(scope="module")
def store(tmp_path_factory) -> ResultStore:
    result_store = ResultStore(tmp_path_factory.mktemp("artifacts"))
    pool_path = destination_pool_path(result_store, OSGB36_RUN)
    pool_path.parent.mkdir(parents=True)
    save_destination_pool(generate_destinations(OSGB36_RUN.seed, POOL_SIZE, load_population_zones()), pool_path)
    return result_store


def test_an_osgb36_run_is_stored_on_its_own_grid_and_flies_the_same_drones(store):
    published_run = replace(OSGB36_RUN, boundary_datum=BoundaryDatum.WGS84)
    published_row, osgb36_row = execute_run(published_run, store, GIT_HASH), execute_run(OSGB36_RUN, store, GIT_HASH)
    osgb36_grid = load_noise_grid(FINE_CELL_SIZE_M, BoundaryDatum.OSGB36)

    assert build_run_key(OSGB36_RUN) != build_run_key(published_run)
    assert osgb36_row["boundary_datum"] == "osgb36"
    assert osgb36_row[GRID_FINGERPRINT_COLUMN] == calculate_grid_fingerprint(osgb36_grid)
    assert osgb36_row[GRID_FINGERPRINT_COLUMN] != published_row[GRID_FINGERPRINT_COLUMN]
    assert grid_cells(load_stored_grid(store, osgb36_row[GRID_FINGERPRINT_COLUMN])) == grid_cells(osgb36_grid)
    assert len(load_drone_levels(store, build_run_key(OSGB36_RUN))) == len(osgb36_grid.rows)
    for unchanged in ["delivered_orders", "assigned_orders", "airborne_drone_seconds", "mean_trip_distance_m"]:
        assert osgb36_row[unchanged] == published_row[unchanged]
