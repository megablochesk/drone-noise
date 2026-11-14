"""Fine-grid design (Round 4, 100 m, 10 s) on this machine, as one guarded batch.

Usage (from src/):
    python -m experiments.revision.run_fine_grid_pilot --seeds 1 2 3 --workers 3
    python -m experiments.revision.run_fine_grid_pilot --seeds 1 2 3 --single-landing --table-name single_landing_runs.csv
    python -m experiments.revision.run_fine_grid_pilot --seeds 1 --slant-floor --table-name slant_floor_runs.csv
    python -m experiments.revision.run_fine_grid_pilot --seeds 1 --noise-aware --table-name noise_aware_runs.csv
"""
import argparse

from experiments.revision.batch_runner import run_guarded_batch
from experiments.revision.fine_grid_design import (
    PHASE_NAME,
    build_fine_grid_specifications,
    build_noise_aware_specifications,
    build_single_landing_specifications,
    build_slant_floor_specifications,
)
from experiments.revision.phase_outputs import phase_directory, write_phase_table


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--single-landing", action="store_true", help="terminal-phase runs with one landing per delivery")
    parser.add_argument("--slant-floor", action="store_true", help="largest-fleet terminal runs with a floored slant distance")
    parser.add_argument("--noise-aware", action="store_true", help="largest-fleet terminal runs with noise-aware routing")
    parser.add_argument("--table-name", default="runs.csv")
    return parser.parse_args()


def choose_design(arguments: argparse.Namespace):
    if arguments.single_landing:
        return build_single_landing_specifications
    if arguments.slant_floor:
        return build_slant_floor_specifications
    if arguments.noise_aware:
        return build_noise_aware_specifications
    return build_fine_grid_specifications


def main():
    arguments = parse_arguments()
    build_specifications = choose_design(arguments)
    runs = run_guarded_batch(build_specifications(arguments.seeds), arguments.workers)
    write_phase_table(runs, phase_directory(PHASE_NAME), arguments.table_name)


if __name__ == "__main__":
    main()
