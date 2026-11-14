"""Redraw the phase 6-12 figures from the stored tables and artefacts, without recomputing anything.

Usage (from src/): python -m experiments.revision.redraw_figures
"""
import matplotlib

matplotlib.use("Agg")  # these scripts only write files, also on machines without a display

from pathlib import Path

import numpy as np
import pandas as pd

from experiments.revision.batch_runner import default_result_store
from experiments.revision.phase_outputs import phase_directory
from experiments.revision.revision_figures import (
    PHASE_TITLES,
    plot_depot_layouts,
    plot_energy_share_maps,
    plot_metrics_against_deliveries,
    plot_relative_changes,
    plot_replication_summary,
    plot_source_level_sweep,
    plot_trip_distance_distributions,
)
from experiments.revision.summarise_phase6_replication import load_replication_runs

ENERGY_SHARE_ARTIFACT = "phase8/energy_shares_seed1.npz"


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
