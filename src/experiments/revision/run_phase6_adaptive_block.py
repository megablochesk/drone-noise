"""Phase 6, adaptive stage: add a block of seeds to the configurations of one fleet that need more.

Usage (from src/): python -m experiments.revision.run_phase6_adaptive_block --fleet 1250 --seeds 6 7 8 9 10
"""
import argparse

import pandas as pd

from experiments.revision.batch_runner import run_guarded_batch
from experiments.revision.phase_outputs import phase_directory, write_phase_table
from experiments.revision.revision_design import build_adaptive_specifications

PHASE_NAME = "phase6"
SUMMARY_TABLE_NAME = "replication_summary.csv"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fleet", type=int, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--workers", type=int, default=3)
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    directory = phase_directory(PHASE_NAME)
    summary = pd.read_csv(directory / SUMMARY_TABLE_NAME)
    specifications = build_adaptive_specifications(summary, arguments.fleet, arguments.seeds)
    if not specifications:
        print(f"No configuration of fleet {arguments.fleet} needs more seeds")
        return

    runs = run_guarded_batch(specifications, arguments.workers)
    table_name = f"replication_runs_fleet{arguments.fleet}_seeds{min(arguments.seeds)}-{max(arguments.seeds)}.csv"
    write_phase_table(runs, directory, table_name)


if __name__ == "__main__":
    main()
