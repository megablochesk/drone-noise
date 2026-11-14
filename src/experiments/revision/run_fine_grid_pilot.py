"""Fine-grid design (Round 4, 100 m, 10 s) on this machine, as one guarded batch.

Usage (from src/): python -m experiments.revision.run_fine_grid_pilot --seeds 1 2 3 --workers 3
"""
import argparse

from experiments.revision.batch_runner import run_guarded_batch
from experiments.revision.fine_grid_design import PHASE_NAME, build_fine_grid_specifications
from experiments.revision.phase_outputs import phase_directory, write_phase_table


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--table-name", default="runs.csv")
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    runs = run_guarded_batch(build_fine_grid_specifications(arguments.seeds), arguments.workers)
    write_phase_table(runs, phase_directory(PHASE_NAME), arguments.table_name)


if __name__ == "__main__":
    main()
