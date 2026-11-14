"""Drawing of the revision figures (phases 6 to 12, Round 4 baseline, fine grid).

Kept apart from the scripts that run or summarise, so that figures can be redrawn without importing them.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from common.model_configs import model_config
from depots.depot_layouts import (
    ACTUAL_LAYOUT,
    POPULATION_KMEANS_LAYOUT,
    RANDOM_DRAW_LAYOUTS,
    RING_LAYOUT,
    SINGLE_HUB_LAYOUT,
    load_population_centre,
    load_study_boundary,
    resolve_depot_layout,
)
from experiments.revision.fine_grid_design import FINE_BASELINE_NOISE_MAP, FINE_CELL_SIZE_M
from experiments.revision.plot_style import (
    FLIGHT_PROFILE_LABELS,
    FLIGHT_PROFILE_LINE_STYLES,
    METRIC_LABELS,
    MILLIONS_FORMATTER,
    SIGNED_PERCENT_FORMATTER,
    STOCKING_COLOURS,
    STOCKING_LABELS,
    STOCKING_ORDER,
    THOUSANDS_FORMATTER,
    add_figure_legend,
    describe_series,
    describe_variant,
)
from experiments.revision.reduced_design import BASELINE_VARIANT
from experiments.revision.result_store import ResultStore, load_drone_levels, load_trip_distances
from experiments.revision.run_executor import DELIVERY_RANGE_M
from metrics.cell_table import load_cell_table
from metrics.exposure_metrics import combine_levels_db
from noise.noise_grid import NoiseGrid, load_noise_grid, to_grid_image

HEADLINE_METRICS = ("delivered_orders", "mean_noise_increase_db", "newly_exposed_population_55db")
PUBLISHED_SOURCE_LEVEL_DB = model_config.drone.noise_at_source_db
TRIP_HISTOGRAM_BIN_WIDTH_M = 1_000.0
DELIVERY_PLOT_METRICS = ("mean_noise_increase_db", "newly_exposed_population_55db")
SOURCE_SWEEP_METRICS = ("mean_noise_increase_db", "newly_exposed_population_55db", "population_inside_drone_contour_51db")
SEED_POINT_SIZE = 10
SEED_POINT_ALPHA = 0.3
ENERGY_SHARE_TITLES = {
    "samples_below_10m_altitude": "Energy from drone positions below 10 m altitude",
    "samples_within_50m_slant_distance": "Energy from drone positions within 50 m of the cell centroid",
}
PLOTTED_FLEET = 1250
PLOTTED_CHANGES = {
    "mean_noise_increase_db_change": "change of mean noise increase (dB)",
    "delivered_orders_relative_change": "change of deliveries",
    "newly_exposed_population_55db_relative_change": "change of newly exposed population at 55 dB",
}
PHASE_TITLES = {
    "phase9": "Depot layouts",
    "phase10": "One-at-a-time parameters",
    "phase11": "Fleet allocation",
    "phase12": "Demand model",
    "round4_baseline": "Baseline noise map",
}
BASELINE_MAP_LEVEL_RANGE_DB = (40.0, 75.0)
MAP_DIFFERENCE_RANGE_DB = (-15.0, 15.0)
MAPPED_RUN = {"number_of_drones": 1250, "stocking": "closest", "terminal_phases": True, "seed": 1}
MAP_LEVEL_RANGE_DB = (40.0, 75.0)
MAP_INCREASE_RANGE_DB = (0.0, 6.0)
DEPOT_LAYOUTS = (ACTUAL_LAYOUT, SINGLE_HUB_LAYOUT, RING_LAYOUT, POPULATION_KMEANS_LAYOUT, *RANDOM_DRAW_LAYOUTS)
DEPOT_MAP_COLUMNS = 3


def plot_metric_panel(axis, summary: pd.DataFrame, metric: str, terminal_phases: bool):
    panel = summary[(summary["metric"] == metric) & (summary["terminal_phases"] == terminal_phases)]
    for stocking in STOCKING_ORDER:
        line = panel[panel["stocking"] == stocking].sort_values("number_of_drones")
        axis.errorbar(
            line["number_of_drones"], line["mean"], yerr=line["confidence_half_width"],
            marker="o", markersize=4, capsize=3, color=STOCKING_COLOURS[stocking], label=f"{STOCKING_LABELS[stocking]} stocking",
        )
    axis.set_title(FLIGHT_PROFILE_LABELS[terminal_phases], fontsize=9)
    axis.set_xlabel("fleet size (drones)")
    axis.set_ylabel(METRIC_LABELS[metric])
    axis.set_xticks(sorted(panel["number_of_drones"].unique()))
    axis.xaxis.set_major_formatter(THOUSANDS_FORMATTER)
    axis.tick_params(labelbottom=True)
    axis.grid(alpha=0.25)
    if metric != "mean_noise_increase_db":
        axis.yaxis.set_major_formatter(THOUSANDS_FORMATTER)


def plot_replication_summary(summary: pd.DataFrame, figure_path):
    figure, axes = plt.subplots(2, len(HEADLINE_METRICS), figsize=(14, 7.5), sharex=True)
    for row, terminal_phases in enumerate((False, True)):
        for column, metric in enumerate(HEADLINE_METRICS):
            plot_metric_panel(axes[row][column], summary, metric, terminal_phases)
    add_figure_legend(figure, axes[0][0], title="Mean over seeds, bars = 95 % confidence half-width")
    figure.savefig(figure_path, dpi=150)
    plt.close(figure)


def label_fleet_sizes(axis, fleet_means: pd.DataFrame, metric: str):
    for number_of_drones, mean in fleet_means.iterrows():
        axis.annotate(
            f"{number_of_drones:,} drones", (mean["delivered_orders"], mean[metric]),
            textcoords="offset points", xytext=(0, -12), ha="center", fontsize=7, color="0.35",
        )


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


def plot_energy_share_maps(shares: dict[str, np.ndarray], figure_path: Path):
    grid = load_noise_grid()
    figure, axes = plt.subplots(1, len(ENERGY_SHARE_TITLES), figsize=(13, 5))
    for axis, (source, title) in zip(axes, ENERGY_SHARE_TITLES.items()):
        image = axis.imshow(to_grid_image(grid, shares[source]), origin="lower", vmin=0.0, vmax=1.0, cmap="viridis")
        axis.set_title(title, fontsize=10)
        axis.set_xticks([])
        axis.set_yticks([])
        figure.colorbar(image, ax=axis, shrink=0.8, label="share of the cell's drone noise energy")
    figure.suptitle("Greater London, 500 m cells: random stocking, terminal phases, 1,250 drones, seed 1")
    figure.tight_layout()
    figure.savefig(figure_path, dpi=150)
    plt.close(figure)


def plot_change_panel(axis, panel: pd.DataFrame, column: str, axis_label: str):
    table = panel.pivot(index="variant", columns="stocking", values=column)
    stockings = [stocking for stocking in STOCKING_ORDER if stocking in table.columns]
    table = table[stockings].rename(index=describe_variant, columns=lambda stocking: f"{STOCKING_LABELS[stocking]} stocking")
    table.plot.bar(ax=axis, width=0.8, color=[STOCKING_COLOURS[stocking] for stocking in stockings], legend=False)
    axis.axhline(0.0, color="black", linewidth=0.6)
    axis.set_xlabel("")
    axis.set_ylabel(axis_label)
    axis.tick_params(axis="x", labelrotation=35, labelsize=8)
    plt.setp(axis.get_xticklabels(), ha="right")
    axis.grid(axis="y", alpha=0.25)
    if column.endswith("_relative_change"):
        axis.yaxis.set_major_formatter(SIGNED_PERCENT_FORMATTER)


def plot_relative_changes(comparison: pd.DataFrame, figure_path, phase_name: str):
    panel = comparison[(comparison["number_of_drones"] == PLOTTED_FLEET) & (comparison["variant"] != BASELINE_VARIANT)]
    figure, axes = plt.subplots(1, len(PLOTTED_CHANGES), figsize=(16, 5.2))
    for axis, (column, axis_label) in zip(axes, PLOTTED_CHANGES.items()):
        plot_change_panel(axis, panel, column, axis_label)
    title = f"{PHASE_TITLES[phase_name]}: change from the baseline of the same seeds, {PLOTTED_FLEET:,} drones, terminal phases"
    add_figure_legend(figure, axes[0], title=title)
    figure.savefig(figure_path, dpi=150)
    plt.close(figure)


def plot_baseline_maps(grid: NoiseGrid, published_db: np.ndarray, round4_db: np.ndarray, figure_path):
    figure, axes = plt.subplots(1, 3, figsize=(17, 4.8))
    panels = [
        ("Published baseline (banded, 2017 maps)", published_db, "viridis", BASELINE_MAP_LEVEL_RANGE_DB, "level (dB)"),
        ("Round 4 road noise, LAeq,16h", round4_db, "viridis", BASELINE_MAP_LEVEL_RANGE_DB, "level (dB)"),
        ("Round 4 minus published", round4_db - published_db, "RdBu_r", MAP_DIFFERENCE_RANGE_DB, "difference (dB)"),
    ]
    for axis, (title, values, colour_map, (lowest, highest), label) in zip(axes, panels):
        image = axis.imshow(to_grid_image(grid, values), origin="lower", cmap=colour_map, vmin=lowest, vmax=highest)
        axis.set_title(title, fontsize=10)
        axis.set_xticks([])
        axis.set_yticks([])
        figure.colorbar(image, ax=axis, shrink=0.8, label=label)
    figure.suptitle("Baseline noise of the 500 m cells of Greater London (40 dB floor in both maps)")
    figure.tight_layout()
    figure.savefig(figure_path, dpi=150)
    plt.close(figure)


def plot_fine_maps(store: ResultStore, fine_runs: pd.DataFrame, figure_path):
    run = fine_runs.loc[(fine_runs[list(MAPPED_RUN)] == pd.Series(MAPPED_RUN)).all(axis=1)].iloc[0]
    grid, cell_table = load_noise_grid(FINE_CELL_SIZE_M), load_cell_table(FINE_BASELINE_NOISE_MAP, FINE_CELL_SIZE_M)
    drone_levels_db = load_drone_levels(store, run["run_key"])
    increase_db = combine_levels_db(drone_levels_db, cell_table.baseline_levels_db) - cell_table.baseline_levels_db
    panels = [
        ("Round 4 baseline, 100 m cells", cell_table.baseline_levels_db, "viridis", MAP_LEVEL_RANGE_DB, "level (dB)"),
        ("Drone noise alone", drone_levels_db, "viridis", MAP_LEVEL_RANGE_DB, "level (dB)"),
        ("Increase over the baseline", increase_db, "magma", MAP_INCREASE_RANGE_DB, "increase (dB)"),
    ]
    figure, axes = plt.subplots(1, 3, figsize=(18, 5))
    for axis, (title, values, colour_map, (lowest, highest), label) in zip(axes, panels):
        image = axis.imshow(to_grid_image(grid, values), origin="lower", cmap=colour_map, vmin=lowest, vmax=highest)
        axis.set_title(title, fontsize=10)
        axis.set_xticks([])
        axis.set_yticks([])
        figure.colorbar(image, ax=axis, shrink=0.8, label=label)
    figure.suptitle("1,250 drones, best stocking, terminal phases, seed 1: 100 m cells, 10 s step")
    figure.tight_layout()
    figure.savefig(figure_path, dpi=150)
    plt.close(figure)


def plot_depot_layout(axis, layout_name: str):
    boundary, centre, depots = load_study_boundary(), load_population_centre(), resolve_depot_layout(layout_name)
    for polygon in getattr(boundary, "geoms", [boundary]):
        axis.plot(*polygon.exterior.xy, color="0.4", linewidth=0.8)
    axis.scatter(
        [depot.easting for depot in depots.values()], [depot.northing for depot in depots.values()],
        color="crimson", s=40, zorder=3, label="depot",
    )
    axis.scatter([centre.easting], [centre.northing], marker="+", color="black", s=80, zorder=4, label="population-weighted centre")
    axis.set_title(f"{describe_variant(layout_name)} ({len(depots)} depot{'s' if len(depots) > 1 else ''})", fontsize=10)
    axis.set_aspect("equal")
    axis.set_xticks([])
    axis.set_yticks([])


def plot_depot_layouts(figure_path):
    number_of_rows = -(-len(DEPOT_LAYOUTS) // DEPOT_MAP_COLUMNS)
    figure, axes = plt.subplots(number_of_rows, DEPOT_MAP_COLUMNS, figsize=(15, 4.2 * number_of_rows))
    for axis, layout_name in zip(axes.ravel(), DEPOT_LAYOUTS):
        plot_depot_layout(axis, layout_name)
    handles, labels = axes.ravel()[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="upper center", ncol=len(labels), frameon=False, title="Depot layouts, Greater London")
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
    figure.savefig(figure_path, dpi=150)
    plt.close(figure)
