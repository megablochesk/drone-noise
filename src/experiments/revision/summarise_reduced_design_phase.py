"""Phases 9-12: compare every variant of a phase with the baseline of the same seeds.

Usage (from src/): python -m experiments.revision.summarise_reduced_design_phase --phase phase9
"""
import matplotlib

matplotlib.use("Agg")

import argparse
from dataclasses import replace

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from common.enum import OrderDatasetType
from depots.depot_layouts import load_population_centre
from experiments.revision.batch_runner import REPOSITORY_ROOT, default_result_store
from experiments.revision.phase_outputs import phase_directory, write_phase_table
from experiments.revision.reduced_design import (
    BASELINE_VARIANT,
    ONE_AT_A_TIME_CHANGES,
    PHASE_CHANGES,
    compare_variants_with_baseline,
    rank_stockings,
)
from experiments.revision.result_store import load_drone_levels
from experiments.revision.run_guard import ensure_clean_working_tree, read_git_hash
from experiments.revision.run_reduced_design_phase import RUN_TABLE_NAME
from experiments.revision.run_specification import RunSpecification, build_model_config
from metrics.cell_table import load_cell_table
from metrics.map_postprocessing import summarise_exposure_by_distance_band
from noise.noise_grid import load_noise_grid

HEADLINE_METRICS = ["delivered_orders", "mean_trip_distance_m", "mean_noise_increase_db", "newly_exposed_population_55db"]
RANKED_METRICS = ["delivered_orders", "mean_noise_increase_db", "newly_exposed_population_55db"]
CENTRAL_AREA_RADIUS_M = 10_000.0
PLOTTED_FLEET = 1250


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=sorted(PHASE_CHANGES), required=True)
    return parser.parse_args()


def calculate_distances_to_population_centre() -> np.ndarray:
    grid, centre = load_noise_grid(), load_population_centre()
    return np.hypot(grid.centroid_northings - centre.northing, grid.centroid_eastings - centre.easting)


def add_central_area_split(runs: pd.DataFrame) -> pd.DataFrame:
    """Adds the headline metrics for cells within and beyond 10 km of the population-weighted centre."""
    store, cell_table = default_result_store(), load_cell_table()
    distances_m = calculate_distances_to_population_centre()
    splits = [
        summarise_exposure_by_distance_band(
            load_drone_levels(store, run_key), cell_table.baseline_levels_db, cell_table.population,
            distances_m, CENTRAL_AREA_RADIUS_M,
        )
        for run_key in runs["run_key"]
    ]
    return pd.concat([runs.reset_index(drop=True), pd.DataFrame(splits)], axis=1)


def describe_altitude_ladders() -> pd.DataFrame:
    """Phase 10: the climb altitudes each landing delay (and cruise altitude) produces at the 30 s step."""
    reference = RunSpecification(stocking=OrderDatasetType.CLOSEST, number_of_drones=1, terminal_phases=True)
    rows = []
    for variant_name, changes in {BASELINE_VARIANT: {}, **ONE_AT_A_TIME_CHANGES}.items():
        model = build_model_config(replace(reference, **changes))
        rows.append({
            "variant": variant_name, "landing_steps": model.landing_steps,
            "climb_altitudes_m": " ".join(f"{altitude:g}" for altitude in model.intermediate_altitudes_ascending),
            "cruise_altitude_m": model.drone.flight_altitude_m,
        })
    return pd.DataFrame(rows)


def plot_relative_changes(comparison: pd.DataFrame, figure_path, phase_name: str):
    panel = comparison[(comparison["number_of_drones"] == PLOTTED_FLEET) & (comparison["variant"] != BASELINE_VARIANT)]
    metrics = ["delivered_orders", "newly_exposed_population_55db"]
    figure, axes = plt.subplots(1, len(metrics) + 1, figsize=(16, 4.8))
    for axis, column, title in [
        (axes[0], "mean_noise_increase_db_change", "change of mean noise increase (dB)"),
        *[(axis, f"{metric}_relative_change", f"relative change of {metric}") for axis, metric in zip(axes[1:], metrics)],
    ]:
        table = panel.pivot(index="variant", columns="stocking", values=column)
        table.plot.bar(ax=axis, width=0.8)
        axis.axhline(0.0, color="black", linewidth=0.6)
        axis.set_title(title, fontsize=9)
        axis.tick_params(axis="x", labelrotation=45, labelsize=7)
    figure.suptitle(f"{phase_name}: change from the baseline, {PLOTTED_FLEET} drones, mean over seeds")
    figure.tight_layout()
    figure.savefig(figure_path, dpi=150)
    plt.close(figure)


def build_phase_tables(phase_name: str, runs: pd.DataFrame) -> dict[str, pd.DataFrame]:
    metrics = list(HEADLINE_METRICS)
    if phase_name == "phase9":
        runs = add_central_area_split(runs)
        metrics += [column for column in runs.columns if column.endswith(("_within", "_beyond"))]
    comparison = compare_variants_with_baseline(runs, [*metrics, "warehouses_out_of_orders"])
    tables = {
        "comparison_with_baseline": comparison,
        "stocking_rankings": pd.concat([rank_stockings(comparison, metric) for metric in RANKED_METRICS], ignore_index=True),
    }
    if phase_name == "phase10":
        tables["altitude_ladders"] = describe_altitude_ladders()
    return tables


def main():
    arguments = parse_arguments()
    ensure_clean_working_tree(REPOSITORY_ROOT)
    git_hash = read_git_hash(REPOSITORY_ROOT)
    directory = phase_directory(arguments.phase)

    tables = build_phase_tables(arguments.phase, pd.read_csv(directory / RUN_TABLE_NAME))
    for table_name, table in tables.items():
        write_phase_table(table.assign(git_hash=git_hash), directory, f"{table_name}.csv")
    plot_relative_changes(tables["comparison_with_baseline"], directory / "changes_from_baseline.png", arguments.phase)


if __name__ == "__main__":
    main()
