"""Phase 5: the four Phase 1 configurations on the published 100,000-order files and on a large seeded pool.

Usage (from src/): python -m experiments.revision.run_phase5_large_pool --workers 3
"""
import argparse

from experiments.revision.batch_runner import run_guarded_batch
from experiments.revision.phase_outputs import phase_directory, write_phase_table
from experiments.revision.revision_design import build_published_configuration_specifications
from experiments.revision.run_specification import OrderSource

LARGE_POOL_SEED = 1


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=3)
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    specifications = (
        build_published_configuration_specifications(OrderSource.PUBLISHED_DATASET, seed=0)
        + build_published_configuration_specifications(OrderSource.SEEDED_POOL, seed=LARGE_POOL_SEED)
    )
    runs = run_guarded_batch(specifications, arguments.workers)
    write_phase_table(runs, phase_directory("phase5"), "large_pool_runs.csv")


if __name__ == "__main__":
    main()
