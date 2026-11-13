"""Phase 7: post-process every saved drone-only map of the replication runs.

Usage (from src/): python -m experiments.revision.run_phase7_postprocessing
"""
import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from common.model_configs import model_config
from experiments.revision.batch_runner import REPOSITORY_ROOT, default_result_store
from experiments.revision.phase_outputs import phase_directory, write_phase_table
from experiments.revision.plot_style import (
    FLIGHT_PROFILE_LINE_STYLES,
    METRIC_LABELS,
    MILLIONS_FORMATTER,
    STOCKING_COLOURS,
    STOCKING_LABELS,
    STOCKING_ORDER,
    THOUSANDS_FORMATTER,
    add_figure_legend,
    describe_series,
)
from experiments.revision.result_store import ResultStore, load_drone_levels, load_trip_distances
from experiments.revision.run_executor import DELIVERY_RANGE_M
from experiments.revision.run_guard import ensure_clean_working_tree, read_git_hash
from experiments.revision.summarise_phase6_replication import (
    CONFIGURATION_COLUMNS,
    STOCKING_LABELS,
    STOCKING_ORDER,
    load_replication_runs,
)
from metrics.cell_table import CellTable, load_cell_table
from metrics.map_postprocessing import (
    rebase_baseline_default,
    summarise_map_exposure,
    summarise_per_thousand_deliveries,
)

PHASE_NAME = "phase7"
PUBLISHED_SOURCE_LEVEL_DB = model_config.drone.noise_at_source_db
SOURCE_LEVEL_SWEEP_DB = tuple(range(80, 106))
ANNOYANCE_PENALTY_DB = 5.6
BASELINE_DEFAULTS_DB = (35.0, 40.0, 45.0, 50.0)
TRIP_DISTANCE_QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)
RUN_IDENTITY_COLUMNS = ["run_key", "seed", *CONFIGURATION_COLUMNS, "delivered_orders"]
TRIP_HISTOGRAM_BIN_WIDTH_M = 1_000.0
DELIVERY_PLOT_METRICS = ("mean_noise_increase_db", "newly_exposed_population_55db")
SOURCE_SWEEP_METRICS = ("mean_noise_increase_db", "newly_exposed_population_55db", "population_inside_drone_contour_51db")
SEED_POINT_SIZE = 10
SEED_POINT_ALPHA = 0.3


def describe_run(run: pd.Series) -> dict:
    return {column: run[column] for column in RUN_IDENTITY_COLUMNS}


def summarise_run_exposure(run: pd.Series, drone_levels_db: np.ndarray, cell_table: CellTable) -> dict:
    exposure = summarise_map_exposure(drone_levels_db, cell_table.baseline_levels_db, cell_table.population)
    return {**describe_run(run), **exposure, **summarise_per_thousand_deliveries(exposure, run["delivered_orders"])}


def sweep_source_level(run: pd.Series, drone_levels_db: np.ndarray, cell_table: CellTable) -> list[dict]:
    source_levels_db = [*SOURCE_LEVEL_SWEEP_DB, PUBLISHED_SOURCE_LEVEL_DB + ANNOYANCE_PENALTY_DB]
    return [
        {
            **describe_run(run), "noise_at_source_db": source_level_db,
            "is_annoyance_penalty_case": source_level_db == PUBLISHED_SOURCE_LEVEL_DB + ANNOYANCE_PENALTY_DB,
            **summarise_map_exposure(
                drone_levels_db + (source_level_db - PUBLISHED_SOURCE_LEVEL_DB),
                cell_table.baseline_levels_db, cell_table.population,
            ),
        }
        for source_level_db in source_levels_db
    ]


def sweep_baseline_default(run: pd.Series, drone_levels_db: np.ndarray, cell_table: CellTable) -> list[dict]:
    return [
        {
            **describe_run(run), "baseline_default_db": baseline_default_db,
            **summarise_map_exposure(
                drone_levels_db, rebase_baseline_default(cell_table.baseline_levels_db, baseline_default_db),
                cell_table.population,
            ),
        }
        for baseline_default_db in BASELINE_DEFAULTS_DB
    ]


def summarise_trip_distances(run: pd.Series, trip_distances_m: np.ndarray) -> dict:
    quantiles = {
        f"trip_distance_quantile_{int(quantile * 100):02d}_m": np.quantile(trip_distances_m, quantile)
        for quantile in TRIP_DISTANCE_QUANTILES
    }
    return {
        **describe_run(run), "assigned_orders": len(trip_distances_m),
        "mean_trip_distance_m": trip_distances_m.mean(), **quantiles,
        "share_of_trips_beyond_12km_one_way": np.mean(trip_distances_m > DELIVERY_RANGE_M),
        "share_of_trips_beyond_12km_round_trip": np.mean(2.0 * trip_distances_m > DELIVERY_RANGE_M),
    }


def average_over_seeds(table: pd.DataFrame, extra_group_columns: list[str]) -> pd.DataFrame:
    group_columns = [*CONFIGURATION_COLUMNS, *extra_group_columns]
    value_columns = [
        column for column in table.select_dtypes("number").columns if column not in ("seed", *group_columns)
    ]
    grouped = table.groupby(group_columns, sort=True)[value_columns]
    means = grouped.mean().add_suffix("_mean")
    deviations = grouped.std(ddof=1).add_suffix("_sd")
    return pd.concat([grouped.size().rename("number_of_seeds"), means, deviations], axis=1).reset_index()


def plot_source_level_sweep(sweep_means: pd.DataFrame, figure_path):
    largest_fleet = sweep_means["number_of_drones"].max()
    panel = sweep_means[(sweep_means["number_of_drones"] == largest_fleet) & ~sweep_means["is_annoyance_penalty_case"]]
    figure, axes = plt.subplots(1, len(SOURCE_SWEEP_METRICS), figsize=(15, 5))
    for axis, metric in zip(axes, SOURCE_SWEEP_METRICS):
        for stocking in STOCKING_ORDER:
            for terminal_phases, line_style in FLIGHT_PROFILE_LINE_STYLES.items():
                line = panel[(panel["stocking"] == stocking) & (panel["terminal_phases"] == terminal_phases)]
                axis.plot(
                    line["noise_at_source_db"], line[f"{metric}_mean"], line_style,
                    color=STOCKING_COLOURS[stocking], label=describe_series(stocking, terminal_phases),
                )
        axis.axvline(PUBLISHED_SOURCE_LEVEL_DB, color="grey", linewidth=0.8)
        axis.annotate(
            f"published {PUBLISHED_SOURCE_LEVEL_DB:g} dB", (PUBLISHED_SOURCE_LEVEL_DB, 0.97),
            xycoords=("data", "axes fraction"), rotation=90, ha="right", va="top", fontsize=7, color="0.35",
        )
        axis.set_xlabel("source level at 1 m (dB)")
        axis.set_ylabel(METRIC_LABELS[metric] + ("" if metric == "mean_noise_increase_db" else " (millions)"))
        axis.grid(alpha=0.25)
        if metric != "mean_noise_increase_db":
            axis.yaxis.set_major_formatter(MILLIONS_FORMATTER)
    add_figure_legend(figure, axes[0], title=f"Source-level sweep, {largest_fleet:,} drones, mean over seeds")
    figure.savefig(figure_path, dpi=150)
    plt.close(figure)


def plot_series_against_deliveries(axis, series: pd.DataFrame, metric: str, stocking: str, terminal_phases: bool):
    """One stocking and flight profile: seed runs as faint points, fleet-size means joined by a line."""
    colour = STOCKING_COLOURS[stocking]
    fleet_means = series.groupby("number_of_drones", sort=True)[["delivered_orders", metric]].mean()
    axis.scatter(series["delivered_orders"], series[metric], s=SEED_POINT_SIZE, color=colour, alpha=SEED_POINT_ALPHA, linewidths=0)
    axis.plot(
        fleet_means["delivered_orders"], fleet_means[metric], FLIGHT_PROFILE_LINE_STYLES[terminal_phases],
        color=colour, marker="o", markersize=4, label=describe_series(stocking, terminal_phases),
    )
    return fleet_means


def label_fleet_sizes(axis, fleet_means: pd.DataFrame, metric: str):
    for number_of_drones, mean in fleet_means.iterrows():
        axis.annotate(
            f"{number_of_drones:,} drones", (mean["delivered_orders"], mean[metric]),
            textcoords="offset points", xytext=(0, -12), ha="center", fontsize=7, color="0.35",
        )


def plot_metrics_against_deliveries(exposure: pd.DataFrame, figure_path):
    figure, axes = plt.subplots(1, len(DELIVERY_PLOT_METRICS), figsize=(12, 5.2))
    for axis, metric in zip(axes, DELIVERY_PLOT_METRICS):
        for stocking in STOCKING_ORDER:
            for terminal_phases in FLIGHT_PROFILE_LINE_STYLES:
                series = exposure[(exposure["stocking"] == stocking) & (exposure["terminal_phases"] == terminal_phases)]
                fleet_means = plot_series_against_deliveries(axis, series, metric, stocking, terminal_phases)
                if stocking == STOCKING_ORDER[0] and not terminal_phases:
                    label_fleet_sizes(axis, fleet_means, metric)
        axis.set_xlabel(METRIC_LABELS["delivered_orders"])
        axis.set_ylabel(METRIC_LABELS[metric])
        axis.xaxis.set_major_formatter(THOUSANDS_FORMATTER)
        axis.grid(alpha=0.25)
    axes[1].yaxis.set_major_formatter(THOUSANDS_FORMATTER)
    add_figure_legend(
        figure, axes[0], title="Lines join fleet-size means; faint points are single seeds",
        number_of_columns=len(STOCKING_ORDER),
    )
    figure.savefig(figure_path, dpi=150)
    plt.close(figure)


def plot_trip_distance_distributions(runs: pd.DataFrame, store: ResultStore, figure_path):
    largest_fleet = runs["number_of_drones"].max()
    largest_fleet_runs = runs[(runs["number_of_drones"] == largest_fleet) & ~runs["terminal_phases"]]
    figure, axis = plt.subplots(figsize=(8, 4.5))
    for stocking in STOCKING_ORDER:
        run_keys = largest_fleet_runs.loc[largest_fleet_runs["stocking"] == stocking, "run_key"]
        distances_km = np.concatenate([load_trip_distances(store, run_key) for run_key in run_keys]) / 1_000.0
        bins = np.arange(0.0, distances_km.max() + 1.0, TRIP_HISTOGRAM_BIN_WIDTH_M / 1_000.0)
        axis.hist(
            distances_km, bins=bins, density=True, histtype="step",
            color=STOCKING_COLOURS[stocking], label=f"{STOCKING_LABELS[stocking]} stocking",
        )
    axis.axvline(DELIVERY_RANGE_M / 1_000.0, color="grey", linewidth=0.8, label=f"{DELIVERY_RANGE_M / 1_000.0:g} km delivery range")
    axis.set_xlabel("one-way trip distance (km)")
    axis.set_ylabel("share of trips per km")
    axis.set_title(f"Trips flown, {largest_fleet:,} drones, cruise only, all seeds", fontsize=10)
    axis.legend(frameon=False)
    figure.tight_layout()
    figure.savefig(figure_path, dpi=150)
    plt.close(figure)


def postprocess_runs(runs: pd.DataFrame, store: ResultStore) -> dict[str, pd.DataFrame]:
    cell_table = load_cell_table()
    exposure_rows, source_rows, baseline_rows, trip_rows = [], [], [], []
    for _, run in runs.iterrows():
        drone_levels_db = load_drone_levels(store, run["run_key"])
        exposure_rows.append(summarise_run_exposure(run, drone_levels_db, cell_table))
        source_rows.extend(sweep_source_level(run, drone_levels_db, cell_table))
        baseline_rows.extend(sweep_baseline_default(run, drone_levels_db, cell_table))
        trip_rows.append(summarise_trip_distances(run, load_trip_distances(store, run["run_key"])))
    return {
        "exposure_by_run": pd.DataFrame(exposure_rows),
        "source_level_sweep_by_run": pd.DataFrame(source_rows),
        "baseline_default_sweep_by_run": pd.DataFrame(baseline_rows),
        "trip_distances_by_run": pd.DataFrame(trip_rows),
    }


def summarise_over_seeds(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {
        "exposure_summary": average_over_seeds(tables["exposure_by_run"], []),
        "source_level_sweep_summary": average_over_seeds(
            tables["source_level_sweep_by_run"], ["noise_at_source_db", "is_annoyance_penalty_case"]
        ),
        "baseline_default_sweep_summary": average_over_seeds(
            tables["baseline_default_sweep_by_run"], ["baseline_default_db"]
        ),
        "trip_distances_summary": average_over_seeds(tables["trip_distances_by_run"], []),
    }


def main():
    ensure_clean_working_tree(REPOSITORY_ROOT)
    git_hash = read_git_hash(REPOSITORY_ROOT)
    store, runs, directory = default_result_store(), load_replication_runs(), phase_directory(PHASE_NAME)

    by_run = postprocess_runs(runs, store)
    summaries = summarise_over_seeds(by_run)
    for table_name, table in {**by_run, **summaries}.items():
        write_phase_table(table.assign(git_hash=git_hash), directory, f"{table_name}.csv")

    plot_source_level_sweep(summaries["source_level_sweep_summary"], directory / "source_level_sweep.png")
    plot_metrics_against_deliveries(by_run["exposure_by_run"], directory / "metrics_against_deliveries.png")
    plot_trip_distance_distributions(runs, store, directory / "trip_distance_distributions.png")


if __name__ == "__main__":
    main()
