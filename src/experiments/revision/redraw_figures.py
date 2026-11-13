"""Redraw every revision figure from the stored tables and artefacts, without recomputing anything.

Usage (from src/): python -m experiments.revision.redraw_figures
"""
import matplotlib

matplotlib.use("Agg")

from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

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
from experiments.revision.batch_runner import default_result_store
from experiments.revision.phase_outputs import phase_directory
from experiments.revision.plot_style import describe_variant
from experiments.revision.run_phase7_postprocessing import (
    plot_metrics_against_deliveries,
    plot_source_level_sweep,
    plot_trip_distance_distributions,
)
from experiments.revision.run_phase8_diagnostics import plot_energy_share_maps
from experiments.revision.summarise_phase6_replication import load_replication_runs, plot_replication_summary
from experiments.revision.summarise_reduced_design_phase import PHASE_TITLES, plot_relative_changes

ENERGY_SHARE_ARTIFACT = "phase8/energy_shares_seed1.npz"
DEPOT_LAYOUTS = (ACTUAL_LAYOUT, SINGLE_HUB_LAYOUT, RING_LAYOUT, POPULATION_KMEANS_LAYOUT, *RANDOM_DRAW_LAYOUTS)
DEPOT_MAP_COLUMNS = 3


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


def redraw_replication_figures():
    phase6, phase7, store = phase_directory("phase6"), phase_directory("phase7"), default_result_store()
    plot_replication_summary(pd.read_csv(phase6 / "replication_summary.csv"), phase6 / "replication_summary.png")
    plot_source_level_sweep(pd.read_csv(phase7 / "source_level_sweep_summary.csv"), phase7 / "source_level_sweep.png")
    plot_metrics_against_deliveries(pd.read_csv(phase7 / "exposure_by_run.csv"), phase7 / "metrics_against_deliveries.png")
    plot_trip_distance_distributions(load_replication_runs(), store, phase7 / "trip_distance_distributions.png")


def redraw_energy_share_maps():
    with np.load(Path(default_result_store().root) / ENERGY_SHARE_ARTIFACT) as shares:
        plot_energy_share_maps(dict(shares), phase_directory("phase8") / "terminal_energy_shares_seed1.png")


def redraw_reduced_design_figures():
    for phase_name in PHASE_TITLES:
        directory = phase_directory(phase_name)
        comparison = pd.read_csv(directory / "comparison_with_baseline.csv")
        plot_relative_changes(comparison, directory / "changes_from_baseline.png", phase_name)


def main():
    redraw_replication_figures()
    redraw_energy_share_maps()
    redraw_reduced_design_figures()
    plot_depot_layouts(phase_directory("phase9") / "depot_layouts.png")


if __name__ == "__main__":
    main()
