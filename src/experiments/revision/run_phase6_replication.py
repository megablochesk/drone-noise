"""Phase 6: replicate fleet x stocking x terminal mode over seeds.

Usage (from src/): python -m experiments.revision.run_phase6_replication --seeds 1 2 3 4 5 --workers 3
"""
import argparse

from experiments.revision.batch_runner import run_guarded_batch
from experiments.revision.phase_outputs import phase_directory, write_phase_table
from experiments.revision.revision_design import ALL_STOCKINGS, PILOT_FLEETS, TERMINAL_MODES, build_factorial_specifications


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--fleets", type=int, nargs="+", default=list(PILOT_FLEETS))
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--table-name", default="replication_runs.csv")
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    specifications = build_factorial_specifications(
        arguments.seeds, arguments.fleets, list(ALL_STOCKINGS), list(TERMINAL_MODES)
    )
    runs = run_guarded_batch(specifications, arguments.workers)
    write_phase_table(runs, phase_directory("phase6"), arguments.table_name)


if __name__ == "__main__":
    main()
