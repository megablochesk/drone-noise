"""Phase 6: replication statistics per configuration and paired stocking differences within seed.

Usage (from src/): python -m experiments.revision.summarise_phase6_replication
"""
import matplotlib

matplotlib.use("Agg")

from pathlib import Path

import pandas as pd
from matplotlib import pyplot as plt

from experiments.revision.batch_runner import REPOSITORY_ROOT
from experiments.revision.phase_outputs import phase_directory, write_phase_table
from experiments.revision.plot_style import (
    FLIGHT_PROFILE_LABELS,
    METRIC_LABELS,
    STOCKING_COLOURS,
    STOCKING_LABELS,
    STOCKING_ORDER,
    THOUSANDS_FORMATTER,
    add_figure_legend,
)
from experiments.revision.run_guard import ensure_clean_working_tree, read_git_hash
from metrics.replication_tables import summarise_metric_by_configuration, summarise_paired_differences_between_levels

PHASE_NAME = "phase6"
RUN_TABLE_PATTERN = "replication_runs*.csv"
HEADLINE_METRICS = ("delivered_orders", "mean_noise_increase_db", "newly_exposed_population_55db")
CONFIGURATION_COLUMNS = ["number_of_drones", "terminal_phases", "stocking"]
RELATIVE_HALF_WIDTH_TARGET = 0.05


def read_run_tables(table_paths: list[Path]) -> pd.DataFrame:
    """All runs of the given tables once each; a block with nothing to run leaves a file without columns."""
    tables = [pd.read_csv(path) for path in table_paths if path.read_text().strip()]
    return pd.concat(tables, ignore_index=True).drop_duplicates(subset="run_key", ignore_index=True)


def load_replication_runs() -> pd.DataFrame:
    return read_run_tables(sorted(phase_directory(PHASE_NAME).glob(RUN_TABLE_PATTERN)))


def summarise_configurations(runs: pd.DataFrame) -> pd.DataFrame:
    summaries = [
        summarise_metric_by_configuration(runs, metric, CONFIGURATION_COLUMNS, RELATIVE_HALF_WIDTH_TARGET)
        for metric in HEADLINE_METRICS
    ]
    return pd.concat(summaries, ignore_index=True).sort_values(["metric", *CONFIGURATION_COLUMNS], ignore_index=True)


def summarise_stocking_differences(runs: pd.DataFrame) -> pd.DataFrame:
    differences = [
        summarise_paired_differences_between_levels(
            runs, metric, level_column="stocking", pair_column="seed", group_columns=["number_of_drones", "terminal_phases"]
        )
        for metric in HEADLINE_METRICS
    ]
    return pd.concat(differences, ignore_index=True)


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


def main():
    ensure_clean_working_tree(REPOSITORY_ROOT)
    git_hash = read_git_hash(REPOSITORY_ROOT)
    runs = load_replication_runs()
    summary = summarise_configurations(runs).assign(git_hash=git_hash)
    differences = summarise_stocking_differences(runs).assign(git_hash=git_hash)

    directory = phase_directory(PHASE_NAME)
    write_phase_table(summary, directory, "replication_summary.csv")
    write_phase_table(differences, directory, "paired_stocking_differences.csv")
    plot_replication_summary(summary, directory / "replication_summary.png")


if __name__ == "__main__":
    main()
