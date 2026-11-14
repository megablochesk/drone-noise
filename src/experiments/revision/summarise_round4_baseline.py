"""Round 4 baseline: what the map looks like next to the published one, and how the floor and the averaging
rule move the exposure metrics of the stored reduced-design runs.

Usage (from src/): python -m experiments.revision.summarise_round4_baseline
"""
import matplotlib

matplotlib.use("Agg")  # these scripts only write files, also on machines without a display

import numpy as np
import pandas as pd

from common.enum import BaselineNoiseMap, LevelAveraging
from datasets.round4_baseline import BASELINE_FLOOR_DB, calculate_round4_cell_levels
from experiments.revision.batch_runner import REPOSITORY_ROOT, default_result_store
from experiments.revision.phase_outputs import phase_directory, write_phase_table
from experiments.revision.reduced_design import ALL_STOCKINGS, build_baseline_specifications
from experiments.revision.result_store import load_drone_levels
from experiments.revision.revision_figures import plot_baseline_maps
from experiments.revision.run_guard import ensure_clean_working_tree, read_git_hash
from experiments.revision.run_specification import build_run_key, specification_to_record
from metrics.cell_table import load_cell_table
from metrics.map_postprocessing import HEADLINE_THRESHOLD_DB
from metrics.exposure_metrics import calculate_mean_noise_increase_db, calculate_newly_exposed_population
from noise.noise_grid import NoiseGrid, load_noise_grid

PHASE_NAME = "round4_baseline"
ALTERNATIVE_FLOORS_DB = (30.0, 35.0)


def summarise_baseline_levels(levels_db: np.ndarray, population: np.ndarray, floor_db: float) -> dict:
    is_loud = levels_db >= HEADLINE_THRESHOLD_DB
    return {
        "mean_level_db": levels_db.mean(),
        "minimum_level_db": levels_db.min(),
        "maximum_level_db": levels_db.max(),
        "share_of_cells_at_floor": np.mean(levels_db == floor_db),
        "share_of_cells_at_or_above_55db": np.mean(is_loud),
        "population_at_or_above_55db": population[is_loud].sum(),
        "population_weighted_mean_level_db": np.average(levels_db, weights=population),
    }


def summarise_exposure_under_baselines(
        drone_levels_db: np.ndarray, baselines: dict[str, np.ndarray], population: np.ndarray
) -> pd.DataFrame:
    """The headline metrics of one drone-only map against each named baseline."""
    return pd.DataFrame([
        {
            "baseline": name,
            "mean_noise_increase_db": calculate_mean_noise_increase_db(drone_levels_db, baseline_levels_db),
            "newly_exposed_population_55db": calculate_newly_exposed_population(
                drone_levels_db, baseline_levels_db, population, HEADLINE_THRESHOLD_DB
            ),
        }
        for name, baseline_levels_db in baselines.items()
    ])


def select_grid_cells(grid: NoiseGrid, cell_levels_db: np.ndarray) -> np.ndarray:
    return cell_levels_db[grid.rows, grid.columns]


def build_alternative_baselines(grid: NoiseGrid) -> dict[str, np.ndarray]:
    """Published map, the Round 4 file, and Round 4 with lower floors or energy averaging."""
    baselines = {
        "published": load_cell_table().baseline_levels_db,
        "round 4, arithmetic mean, 40 dB floor": load_cell_table(BaselineNoiseMap.ROUND_4_ROAD).baseline_levels_db,
    }
    for floor_db in ALTERNATIVE_FLOORS_DB:
        cell_levels_db = calculate_round4_cell_levels(LevelAveraging.ARITHMETIC, floor_db)
        baselines[f"round 4, arithmetic mean, {floor_db:g} dB floor"] = select_grid_cells(grid, cell_levels_db)
    energy_levels_db = calculate_round4_cell_levels(LevelAveraging.ENERGY, BASELINE_FLOOR_DB)
    baselines["round 4, energy mean, 40 dB floor"] = select_grid_cells(grid, energy_levels_db)
    return baselines


def describe_baselines(baselines: dict[str, np.ndarray], population: np.ndarray) -> pd.DataFrame:
    rows = [
        {"baseline": name, **summarise_baseline_levels(levels_db, population, levels_db.min())}
        for name, levels_db in baselines.items()
    ]
    return pd.DataFrame(rows)


def compare_stored_runs_under_baselines(baselines: dict[str, np.ndarray], population: np.ndarray) -> pd.DataFrame:
    """Every published-baseline run of the reduced design, re-measured against each baseline; mean over seeds."""
    store, tables = default_result_store(), []
    for specification in build_baseline_specifications(ALL_STOCKINGS):
        drone_levels_db = load_drone_levels(store, build_run_key(specification))
        record = specification_to_record(specification)
        table = summarise_exposure_under_baselines(drone_levels_db, baselines, population)
        tables.append(table.assign(number_of_drones=record["number_of_drones"], stocking=record["stocking"], seed=record["seed"]))
    runs = pd.concat(tables, ignore_index=True)
    grouped = runs.groupby(["number_of_drones", "stocking", "baseline"], sort=False)
    return grouped[["mean_noise_increase_db", "newly_exposed_population_55db"]].mean().reset_index()


def main():
    ensure_clean_working_tree(REPOSITORY_ROOT)
    git_hash = read_git_hash(REPOSITORY_ROOT)
    directory, grid, population = phase_directory(PHASE_NAME), load_noise_grid(), load_cell_table().population

    baselines = build_alternative_baselines(grid)
    tables = {
        "baseline_maps.csv": describe_baselines(baselines, population),
        "exposure_under_baselines.csv": compare_stored_runs_under_baselines(baselines, population),
    }
    for file_name, table in tables.items():
        write_phase_table(table.assign(git_hash=git_hash), directory, file_name)
    plot_baseline_maps(
        grid, baselines["published"], baselines["round 4, arithmetic mean, 40 dB floor"], directory / "baseline_maps.png"
    )


if __name__ == "__main__":
    main()
