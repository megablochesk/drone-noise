"""Phase 8a/8b runs: minimum slant distance and 10 s time step, compared with the default runs of the same seeds.

Usage (from src/): python -m experiments.revision.run_phase8_batches --workers 3
"""
import argparse
from dataclasses import replace

from common.enum import OrderDatasetType
from experiments.revision.batch_runner import run_guarded_batch
from experiments.revision.phase_outputs import phase_directory, write_phase_table
from experiments.revision.revision_design import (
    ALL_STOCKINGS,
    REDUCED_DESIGN_FLEETS,
    REDUCED_DESIGN_SEEDS,
    build_factorial_specifications,
)
from experiments.revision.run_specification import RunSpecification, build_run_key

PHASE_NAME = "phase8"
LARGEST_FLEET = 1250
MINIMUM_SLANT_DISTANCES_M = (0.0, 10.0, 25.0)
TIME_STEPS_S = (30, 10)
TIME_STEP_SEED = 1


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=3)
    return parser.parse_args()


def build_minimum_slant_distance_specifications() -> list[RunSpecification]:
    """8a: terminal phases, 1,250 drones, random stocking, with and without a slant-distance floor."""
    default_runs = build_factorial_specifications(
        list(REDUCED_DESIGN_SEEDS), [LARGEST_FLEET], [OrderDatasetType.RANDOM], terminal_modes=[True]
    )
    return [
        replace(specification, minimum_slant_distance_m=minimum_slant_distance_m)
        for minimum_slant_distance_m in MINIMUM_SLANT_DISTANCES_M
        for specification in default_runs
    ]


def build_time_step_specifications() -> list[RunSpecification]:
    """8b: no terminal phases for every stocking, plus best stocking with terminal phases, at 30 s and 10 s."""
    cruise_only = build_factorial_specifications(
        [TIME_STEP_SEED], list(REDUCED_DESIGN_FLEETS), list(ALL_STOCKINGS), terminal_modes=[False]
    )
    best_with_terminal = build_factorial_specifications(
        [TIME_STEP_SEED], list(REDUCED_DESIGN_FLEETS), [OrderDatasetType.CLOSEST], terminal_modes=[True]
    )
    return [
        replace(specification, time_step_s=time_step_s)
        for time_step_s in TIME_STEPS_S
        for specification in cruise_only + best_with_terminal
    ]


def select_runs(runs, specifications: list[RunSpecification]):
    run_keys = [build_run_key(specification) for specification in specifications]
    return runs.drop_duplicates(subset="run_key").set_index("run_key").loc[run_keys].reset_index()


def main():
    arguments = parse_arguments()
    slant_specifications = build_minimum_slant_distance_specifications()
    time_step_specifications = build_time_step_specifications()
    runs = run_guarded_batch(slant_specifications + time_step_specifications, arguments.workers)

    directory = phase_directory(PHASE_NAME)
    write_phase_table(select_runs(runs, slant_specifications), directory, "minimum_slant_distance_runs.csv")
    write_phase_table(select_runs(runs, time_step_specifications), directory, "time_step_runs.csv")


if __name__ == "__main__":
    main()
