"""Phases 9-12: run every variant of one or more phases on the reduced design, as one guarded batch.

Usage (from src/): python -m experiments.revision.run_reduced_design_phase --phases phase10 phase11 --workers 3
"""
import argparse

from experiments.revision.batch_runner import run_guarded_batch
from experiments.revision.phase_outputs import phase_directory, write_phase_table
from experiments.revision.reduced_design import PHASE_CHANGES, build_phase_variants, label_phase_runs

RUN_TABLE_NAME = "runs.csv"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phases", choices=sorted(PHASE_CHANGES), nargs="+", required=True)
    parser.add_argument("--workers", type=int, default=3)
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    variants_by_phase = {phase_name: build_phase_variants(phase_name) for phase_name in arguments.phases}
    all_specifications = [
        specification
        for variants in variants_by_phase.values() for specifications in variants.values()
        for specification in specifications
    ]

    batch_runs = run_guarded_batch(all_specifications, arguments.workers)
    for phase_name, variants in variants_by_phase.items():
        write_phase_table(label_phase_runs(batch_runs, variants), phase_directory(phase_name), RUN_TABLE_NAME)


if __name__ == "__main__":
    main()
