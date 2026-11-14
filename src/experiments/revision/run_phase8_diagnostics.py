"""Phase 8 diagnostics that need no new batch: energy shares (8a), comparison tables (8a-8c), single events (8d).

Usage (from src/): python -m experiments.revision.run_phase8_diagnostics
"""
import matplotlib

matplotlib.use("Agg")

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from common.enum import OrderDatasetType
from common.model_configs import ModelConfig, model_config
from depots.depot_layouts import resolve_depot_layout
from experiments.revision.batch_runner import REPOSITORY_ROOT, default_result_store
from experiments.revision.phase8_tables import (
    compare_minimum_slant_distances,
    compare_time_steps,
    summarise_energy_shares,
    summarise_round_trip_times,
)
from experiments.revision.phase_outputs import phase_directory, write_artifact_provenance, write_phase_table
from experiments.revision.revision_design import REDUCED_DESIGN_SEEDS, REVISION_POOL_SIZE
from experiments.revision.run_executor import HEADLINE_EXPOSURE_THRESHOLD_DB, plan_demand, run_simulation
from experiments.revision.run_guard import ensure_clean_working_tree, read_git_hash
from experiments.revision.run_specification import RunSpecification
from experiments.revision.single_event_checks import (
    simulate_single_delivery,
    summarise_straight_pass,
    summarise_terminal_event,
)
from experiments.revision.summarise_phase6_replication import load_replication_runs
from metrics.cell_table import load_cell_table
from metrics.exposure_metrics import find_newly_exposed_cells
from noise.energy_diagnostics import calculate_low_altitude_energy_shares, calculate_nearby_energy_shares
from noise.noise_grid import load_noise_grid, to_grid_image

PHASE_NAME = "phase8"
LARGEST_FLEET = 1250
LOW_ALTITUDE_LIMIT_M = 10.0
NEARBY_SLANT_DISTANCE_LIMIT_M = 50.0
SINGLE_EVENT_TIME_STEPS_S = (30, 10, 1)
FAA_STRAIGHT_PASS_SEL_DB = 61.0
FAA_DELIVERY_SEL_RANGES_DB = {20.0: (90.5, 91.8), 75.0: (81.6, 83.7), 195.0: (76.5, 78.8), 372.0: (70.4, 74.5)}


def calculate_energy_shares_for_seed(seed: int) -> dict[str, np.ndarray]:
    """Re-flies random stocking with terminal phases at 1,250 drones and splits each cell's drone energy."""
    specification = RunSpecification(
        stocking=OrderDatasetType.RANDOM, number_of_drones=LARGEST_FLEET, terminal_phases=True,
        seed=seed, pool_size=REVISION_POOL_SIZE,
    )
    depots = resolve_depot_layout(specification.depot_layout)
    simulator = run_simulation(specification, plan_demand(specification, default_result_store(), depots))
    tracker, grid = simulator.noise_monitor.tracker, load_noise_grid()
    cells = (grid.centroid_northings, grid.centroid_eastings)
    return {
        "drone_levels_db": tracker.calculate_drone_noise_levels(),
        "samples_below_10m_altitude": calculate_low_altitude_energy_shares(*cells, tracker.samples, LOW_ALTITUDE_LIMIT_M),
        "samples_within_50m_slant_distance": calculate_nearby_energy_shares(
            *cells, tracker.samples, NEARBY_SLANT_DISTANCE_LIMIT_M
        ),
    }


def summarise_seed_energy_shares(seed: int, shares: dict[str, np.ndarray]) -> list[dict]:
    cell_table = load_cell_table()
    newly_exposed = find_newly_exposed_cells(
        shares["drone_levels_db"], cell_table.baseline_levels_db, HEADLINE_EXPOSURE_THRESHOLD_DB
    )
    return [
        {"seed": seed, "energy_source": source, **summarise_energy_shares(shares[source], cell_table.population, newly_exposed)}
        for source in ("samples_below_10m_altitude", "samples_within_50m_slant_distance")
    ]

ENERGY_SHARE_TITLES = {
    "samples_below_10m_altitude": "Energy from drone positions below 10 m altitude",
    "samples_within_50m_slant_distance": "Energy from drone positions within 50 m of the cell centroid",
}


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


def analyse_energy_shares(directory: Path, git_hash: str) -> pd.DataFrame:
    artifact_directory = Path(default_result_store().root) / PHASE_NAME
    artifact_directory.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in REDUCED_DESIGN_SEEDS:
        shares = calculate_energy_shares_for_seed(seed)
        shares_path = artifact_directory / f"energy_shares_seed{seed}.npz"
        np.savez_compressed(shares_path, **shares)
        write_artifact_provenance(shares_path, git_hash, command=" ".join(sys.argv))
        rows.extend(summarise_seed_energy_shares(seed, shares))
        if seed == REDUCED_DESIGN_SEEDS[0]:
            plot_energy_share_maps(shares, directory / "terminal_energy_shares_seed1.png")
    return pd.DataFrame(rows)


def with_time_step(time_step_s: int) -> ModelConfig:
    return replace(model_config, time=replace(model_config.time, step_s=time_step_s))


def build_straight_pass_table() -> pd.DataFrame:
    table = pd.DataFrame([summarise_straight_pass(with_time_step(time_step_s)) for time_step_s in SINGLE_EVENT_TIME_STEPS_S])
    return table.assign(faa_measurement_scaled_to_100m_sel_db=FAA_STRAIGHT_PASS_SEL_DB)


def build_terminal_event_table() -> pd.DataFrame:
    tables = []
    for time_step_s in SINGLE_EVENT_TIME_STEPS_S[:2]:
        delivery = simulate_single_delivery(with_time_step(time_step_s), terminal_phases=True)
        table = summarise_terminal_event(delivery, list(FAA_DELIVERY_SEL_RANGES_DB)).assign(time_step_s=time_step_s)
        table["faa_low_sel_db"] = [FAA_DELIVERY_SEL_RANGES_DB[distance][0] for distance in table["horizontal_distance_ft"]]
        table["faa_high_sel_db"] = [FAA_DELIVERY_SEL_RANGES_DB[distance][1] for distance in table["horizontal_distance_ft"]]
        table["terminal_event_minus_faa_midpoint_db"] = (
            table["terminal_event_sel_db"] - (table["faa_low_sel_db"] + table["faa_high_sel_db"]) / 2.0
        )
        tables.append(table)
    return pd.concat(tables, ignore_index=True)


def build_batch_comparisons(directory: Path) -> dict[str, pd.DataFrame]:
    """Comparison tables for the batches that have been run (see run_phase8_batches.py)."""
    comparisons = {"round_trip_times": summarise_round_trip_times(load_replication_runs())}
    slant_runs_path, time_step_runs_path = directory / "minimum_slant_distance_runs.csv", directory / "time_step_runs.csv"
    if slant_runs_path.exists():
        comparisons["minimum_slant_distance_changes"] = compare_minimum_slant_distances(pd.read_csv(slant_runs_path))
    if time_step_runs_path.exists():
        comparisons["time_step_comparison"] = compare_time_steps(pd.read_csv(time_step_runs_path))
    return comparisons


def main():
    ensure_clean_working_tree(REPOSITORY_ROOT)
    git_hash = read_git_hash(REPOSITORY_ROOT)
    directory = phase_directory(PHASE_NAME)
    directory.mkdir(parents=True, exist_ok=True)

    tables = {
        "straight_pass_sel": build_straight_pass_table(),
        "terminal_event_sel": build_terminal_event_table(),
        **build_batch_comparisons(directory),
        "terminal_energy_shares": analyse_energy_shares(directory, git_hash),
    }
    for table_name, table in tables.items():
        write_phase_table(table.assign(git_hash=git_hash), directory, f"{table_name}.csv")


if __name__ == "__main__":
    main()
