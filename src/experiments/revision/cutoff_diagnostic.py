"""Diagnostic: what the noise sum loses when positions beyond a maximum slant distance are left out.

The model sums every distinct position, weighted by its count, for every cell. A cut-off would let a spatial index skip most pairs; this
measures the error it would cause on one run, against the exact sum. The default stays without a cut-off.

Usage (from src/): python -m experiments.revision.cutoff_diagnostic
"""
import numpy as np
import pandas as pd

from common.enum import OrderDatasetType
from depots.depot_layouts import resolve_depot_layout
from experiments.revision.batch_runner import REPOSITORY_ROOT, default_result_store
from experiments.revision.fine_grid_design import PHASE_NAME, build_fine_grid_specifications
from experiments.revision.phase_outputs import phase_directory, write_phase_table
from experiments.revision.run_executor import HEADLINE_EXPOSURE_THRESHOLD_DB, plan_demand, run_simulation
from experiments.revision.run_guard import ensure_clean_working_tree, read_git_hash
from experiments.revision.run_specification import RunSpecification, build_run_key
from metrics.cell_table import load_cell_table
from metrics.exposure_metrics import calculate_mean_noise_increase_db, calculate_newly_exposed_population, combine_levels_db
from noise.energy_noise import (
    FlightSamples,
    calculate_equivalent_levels_db,
    count_distinct_samples,
    sum_inverse_squared_distances_of_distinct_samples,
)

MAXIMUM_SLANT_DISTANCES_M = (np.inf, 10_000.0, 5_000.0, 2_000.0, 1_000.0, 500.0)
DIAGNOSED_FLEET = 500
DIAGNOSED_STOCKING = OrderDatasetType.CLOSEST
DIAGNOSED_SEED = 1
NO_FLOOR_M = 0.0


def calculate_levels_within_cutoffs(
        cell_northings: np.ndarray, cell_eastings: np.ndarray, samples: FlightSamples, number_of_time_steps: int,
        noise_at_source_db: float, maximum_slant_distances_m: list[float],
) -> dict[float, np.ndarray]:
    """Drone-only level per cell for each cut-off; an infinite cut-off is the exact sum."""
    distinct_samples = count_distinct_samples(samples)
    return {
        maximum_slant_distance_m: calculate_equivalent_levels_db(
            sum_inverse_squared_distances_of_distinct_samples(
                cell_northings, cell_eastings, distinct_samples, NO_FLOOR_M, maximum_slant_distance_m
            ),
            noise_at_source_db, number_of_time_steps,
        )
        for maximum_slant_distance_m in maximum_slant_distances_m
    }


def summarise_cutoff_errors(
        levels_by_cutoff: dict[float, np.ndarray], baseline_levels_db: np.ndarray, population: np.ndarray
) -> pd.DataFrame:
    """Per cut-off: headline metrics and the largest error of the combined level against the exact sum."""
    exact_combined_levels_db = combine_levels_db(baseline_levels_db, levels_by_cutoff[np.inf])
    return pd.DataFrame([
        {
            "maximum_slant_distance_m": maximum_slant_distance_m,
            "largest_combined_level_error_db": np.max(
                np.abs(combine_levels_db(baseline_levels_db, drone_levels_db) - exact_combined_levels_db)
            ),
            "mean_noise_increase_db": calculate_mean_noise_increase_db(drone_levels_db, baseline_levels_db),
            "newly_exposed_population_55db": calculate_newly_exposed_population(
                drone_levels_db, baseline_levels_db, population, HEADLINE_EXPOSURE_THRESHOLD_DB
            ),
        }
        for maximum_slant_distance_m, drone_levels_db in levels_by_cutoff.items()
    ])


def select_diagnosed_specification() -> RunSpecification:
    """Best stocking with terminal phases: the configuration with the most low-altitude positions."""
    return next(
        specification for specification in build_fine_grid_specifications([DIAGNOSED_SEED])
        if specification.number_of_drones == DIAGNOSED_FLEET
        and specification.stocking is DIAGNOSED_STOCKING
        and specification.terminal_phases
    )


def diagnose_cutoffs(specification: RunSpecification) -> pd.DataFrame:
    store = default_result_store()
    demand = plan_demand(specification, store, resolve_depot_layout(specification.depot_layout))
    tracker = run_simulation(specification, demand).noise_monitor.tracker
    levels_by_cutoff = calculate_levels_within_cutoffs(
        tracker.grid.centroid_northings, tracker.grid.centroid_eastings, tracker.samples,
        tracker.number_of_time_steps, tracker.noise_at_source_db, list(MAXIMUM_SLANT_DISTANCES_M),
    )
    cell_table = load_cell_table(specification.baseline_noise_map, specification.noise_cell_m)
    return summarise_cutoff_errors(levels_by_cutoff, cell_table.baseline_levels_db, cell_table.population)


def main():
    ensure_clean_working_tree(REPOSITORY_ROOT)
    specification = select_diagnosed_specification()
    table = diagnose_cutoffs(specification).assign(
        run_key=build_run_key(specification), git_hash=read_git_hash(REPOSITORY_ROOT)
    )
    write_phase_table(table, phase_directory(PHASE_NAME), "cutoff_distance_errors.csv")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
