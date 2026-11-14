"""Phase 6: replication statistics per configuration and paired stocking differences within seed.

Usage (from src/): python -m experiments.revision.summarise_phase6_replication
"""
import matplotlib

matplotlib.use("Agg")  # these scripts only write files, also on machines without a display

from pathlib import Path

import pandas as pd

from experiments.revision.batch_runner import REPOSITORY_ROOT
from experiments.revision.phase_outputs import phase_directory, write_phase_table
from experiments.revision.revision_figures import HEADLINE_METRICS, plot_replication_summary
from experiments.revision.run_guard import ensure_clean_working_tree, read_git_hash
from metrics.replication_tables import summarise_metric_by_configuration, summarise_paired_differences_between_levels

PHASE_NAME = "phase6"
RUN_TABLE_PATTERN = "replication_runs*.csv"
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
