"""Phases 9-12: run every variant of a phase on the reduced design.

Usage (from src/): python -m experiments.revision.run_reduced_design_phase --phase phase9 --workers 3
"""
import argparse

from experiments.revision.batch_runner import run_guarded_batch
from experiments.revision.phase_outputs import phase_directory, write_phase_table
from experiments.revision.reduced_design import PHASE_CHANGES, build_phase_variants
from experiments.revision.run_specification import build_run_key

RUN_TABLE_NAME = "runs.csv"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=sorted(PHASE_CHANGES), required=True)
    parser.add_argument("--workers", type=int, default=3)
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    variants = build_phase_variants(arguments.phase)
    variant_by_run_key = {
        build_run_key(specification): variant_name
        for variant_name, specifications in variants.items() for specification in specifications
    }
    all_specifications = [specification for specifications in variants.values() for specification in specifications]

    runs = run_guarded_batch(all_specifications, arguments.workers)
    runs.insert(1, "variant", runs["run_key"].map(variant_by_run_key))
    write_phase_table(runs, phase_directory(arguments.phase), RUN_TABLE_NAME)


if __name__ == "__main__":
    main()
