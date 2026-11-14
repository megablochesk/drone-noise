"""Fine-grid pilot (Round 4, 100 m, 10 s): comparison with the 500 m / 30 s runs of the same seeds, the
pixel-level reference for both cell averages of the baseline, and maps.

Usage (from src/): python -m experiments.revision.summarise_fine_grid
"""
from pathlib import Path

import numpy as np
import pandas as pd

from common.enum import BaselineNoiseMap
from common.path_configs import PATH_CONFIGS
from datasets.round4_baseline import BASELINE_FLOOR_DB, read_raster_levels
from experiments.revision.batch_runner import REPOSITORY_ROOT, default_result_store
from experiments.revision.fine_grid_design import FINE_BASELINE_NOISE_MAP, FINE_CELL_SIZE_M, PHASE_NAME
from experiments.revision.phase8_tables import (
    HEADLINE_NOISE_METRIC,
    RELATIVE_METRICS,
    add_changes_from_reference,
    summarise_round_trip_times,
)
from experiments.revision.phase_outputs import phase_directory, write_phase_table
from experiments.revision.result_store import ResultStore, load_drone_levels, load_row
from experiments.revision.revision_design import ALL_STOCKINGS, PILOT_FLEETS, TERMINAL_MODES, build_factorial_specifications
from experiments.revision.revision_figures import plot_fine_maps
from experiments.revision.run_guard import ensure_clean_working_tree, read_git_hash
from experiments.revision.run_specification import build_run_key, specification_to_record
from experiments.revision.summarise_round4_baseline import summarise_exposure_under_baselines
from metrics.cell_table import load_cell_table
from metrics.map_postprocessing import HEADLINE_THRESHOLD_DB
from metrics.pixel_exposure import map_pixels_to_cells, summarise_pixel_level_exposure
from noise.baseline_aggregation import fill_levels_below_floor
from noise.grid_generator import BOUNDARIES
from noise.noise_data_processor import PUBLISHED_CELL_SIZE_M
from noise.noise_grid import load_noise_grid

RUN_TABLE_NAME = "runs.csv"
SINGLE_LANDING_TABLE_NAME = "single_landing_runs.csv"
SLANT_FLOOR_TABLE_NAME = "slant_floor_runs.csv"
CONFIGURATION_KEYS = ["number_of_drones", "stocking", "terminal_phases"]
METRICS = [HEADLINE_NOISE_METRIC, *RELATIVE_METRICS]
CELL_AVERAGES = {
    "arithmetic cell mean": BaselineNoiseMap.ROUND_4_ROAD,
    "energy cell mean": BaselineNoiseMap.ROUND_4_ROAD_ENERGY,
}
PIXEL_REFERENCE = "pixel-level reference"


def compare_fine_with_coarse(fine_runs: pd.DataFrame, coarse_runs: pd.DataFrame) -> pd.DataFrame:
    """Per configuration: mean over the seeds present in both tables, and the mean seed-paired change."""
    pairing = [*CONFIGURATION_KEYS, "seed"]
    for runs in (fine_runs, coarse_runs):
        if runs.duplicated(pairing).any():
            raise ValueError("A table holds more than one run per configuration and seed; split it by variant first")
    changes = add_changes_from_reference(fine_runs, coarse_runs[[*pairing, *METRICS]], pairing)
    value_columns = [column for column in changes.columns if column.startswith(tuple(METRICS))]
    grouped = changes.groupby(CONFIGURATION_KEYS, sort=False)
    return pd.concat([grouped.size().rename("number_of_seeds"), grouped[value_columns].mean()], axis=1).reset_index()


def measure_coarse_runs_against_round4(store: ResultStore, seeds: list[int]) -> pd.DataFrame:
    """The stored 500 m / 30 s pilot runs of these seeds, re-measured against the Round 4 map of the design."""
    cell_table, rows = load_cell_table(FINE_BASELINE_NOISE_MAP, PUBLISHED_CELL_SIZE_M), []
    for specification in build_factorial_specifications(seeds, list(PILOT_FLEETS), list(ALL_STOCKINGS), list(TERMINAL_MODES)):
        run_key = build_run_key(specification)
        exposure = summarise_exposure_under_baselines(
            load_drone_levels(store, run_key), {"round 4": cell_table.baseline_levels_db}, cell_table.population
        ).iloc[0]
        record = specification_to_record(specification)
        rows.append({
            **{key: record[key] for key in [*CONFIGURATION_KEYS, "seed"]},
            "delivered_orders": load_row(store, run_key)["delivered_orders"],
            **exposure.drop("baseline").to_dict(),
        })
    return pd.DataFrame(rows)


def load_filled_pixels():
    """Round 4 pixels with the floor filled in, and the fine cell each pixel centre lies in."""
    raster, grid = read_raster_levels(Path(PATH_CONFIGS.round4_road_noise_raster_path)), load_noise_grid(FINE_CELL_SIZE_M)
    cell_of_pixel = map_pixels_to_cells(
        (raster.easting_edges_m[:-1] + raster.easting_edges_m[1:]) / 2.0,
        (raster.northing_edges_m[:-1] + raster.northing_edges_m[1:]) / 2.0,
        grid.rows, grid.columns, BOUNDARIES.left, BOUNDARIES.bottom, FINE_CELL_SIZE_M,
    )
    pixel_levels_db = fill_levels_below_floor(raster.levels_db, raster.nodata_value, BASELINE_FLOOR_DB).astype(np.float64)
    return pixel_levels_db, cell_of_pixel


def measure_run_under_every_baseline(drone_levels_db: np.ndarray, pixel_levels_db, cell_of_pixel) -> pd.DataFrame:
    baselines = {name: load_cell_table(noise_map, FINE_CELL_SIZE_M).baseline_levels_db for name, noise_map in CELL_AVERAGES.items()}
    population = load_cell_table(FINE_BASELINE_NOISE_MAP, FINE_CELL_SIZE_M).population
    cell_averaged = summarise_exposure_under_baselines(drone_levels_db, baselines, population)
    reference = summarise_pixel_level_exposure(drone_levels_db, population, pixel_levels_db, cell_of_pixel, HEADLINE_THRESHOLD_DB)
    return pd.concat([pd.DataFrame([{"baseline": PIXEL_REFERENCE, **reference}]), cell_averaged], ignore_index=True)


def compare_cell_averages_with_pixels(store: ResultStore, fine_runs: pd.DataFrame) -> pd.DataFrame:
    """Every fine run under the pixel-level reference and both cell averages; mean over seeds."""
    pixel_levels_db, cell_of_pixel = load_filled_pixels()
    tables = [
        measure_run_under_every_baseline(load_drone_levels(store, run.run_key), pixel_levels_db, cell_of_pixel).assign(
            **{key: getattr(run, key) for key in [*CONFIGURATION_KEYS, "seed"]}
        )
        for run in fine_runs.itertuples()
    ]
    grouped = pd.concat(tables, ignore_index=True).groupby([*CONFIGURATION_KEYS, "baseline"], sort=False)
    return grouped[["mean_noise_increase_db", "newly_exposed_population_55db"]].mean().reset_index()


def summarise_single_landing(fine_runs: pd.DataFrame, single_landing_runs: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """One landing per delivery against the published two: metrics by seed pair, and seconds per round trip."""
    cruise_only_runs = fine_runs[~fine_runs["terminal_phases"]]
    return {
        "single_landing_comparison.csv": compare_fine_with_coarse(single_landing_runs, fine_runs),
        "round_trip_times_two_landings.csv": summarise_round_trip_times(fine_runs),
        "round_trip_times_one_landing.csv": summarise_round_trip_times(pd.concat([cruise_only_runs, single_landing_runs])),
    }


def main():
    ensure_clean_working_tree(REPOSITORY_ROOT)
    git_hash = read_git_hash(REPOSITORY_ROOT)
    directory, store = phase_directory(PHASE_NAME), default_result_store()
    fine_runs = pd.read_csv(directory / RUN_TABLE_NAME)
    coarse_runs = measure_coarse_runs_against_round4(store, sorted(fine_runs["seed"].unique().tolist()))

    tables = {
        "comparison_with_coarse_grid.csv": compare_fine_with_coarse(fine_runs, coarse_runs),
        "cell_averages_against_pixels.csv": compare_cell_averages_with_pixels(store, fine_runs),
    }
    if (directory / SINGLE_LANDING_TABLE_NAME).exists():
        tables.update(summarise_single_landing(fine_runs, pd.read_csv(directory / SINGLE_LANDING_TABLE_NAME)))
    if (directory / SLANT_FLOOR_TABLE_NAME).exists():
        slant_floor_runs = pd.read_csv(directory / SLANT_FLOOR_TABLE_NAME)
        tables["slant_floor_comparison.csv"] = compare_fine_with_coarse(slant_floor_runs, fine_runs)
    for file_name, table in tables.items():
        write_phase_table(table.assign(git_hash=git_hash), directory, file_name)
    plot_fine_maps(store, fine_runs, directory / "fine_grid_maps.png")


if __name__ == "__main__":
    main()
