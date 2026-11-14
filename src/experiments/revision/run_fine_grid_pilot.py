"""A design on the fine grid (Round 4, 100 m, 10 s) on this machine, as one guarded batch, written as a run table.

Designs: pilot (fleet x stocking x terminal mode), single-landing, slant-floor, noise-aware, paper-figures.

Usage (from src/):
    python -m experiments.revision.run_fine_grid_pilot --seeds 1 2 3 --workers 3
    python -m experiments.revision.run_fine_grid_pilot --seeds 1 2 3 --design single-landing --table-name single_landing_runs.csv
    python -m experiments.revision.run_fine_grid_pilot --seeds 1 --design paper-figures --table-name paper_figure_runs.csv
    python -m experiments.revision.run_fine_grid_pilot --seeds 1 2 3 --design paper-figures --table-name paper_figure_runs.csv --collect-only
"""
import argparse

from experiments.revision.batch_runner import collect_stored_runs, default_result_store, run_guarded_batch
from experiments.revision.fine_grid_design import DESIGN_BUILDERS, PHASE_NAME, build_design_specifications
from experiments.revision.phase_outputs import phase_directory, write_phase_table

DEFAULT_DESIGN = "pilot"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--design", choices=list(DESIGN_BUILDERS), default=DEFAULT_DESIGN)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--table-name", default="runs.csv")
    parser.add_argument(
        "--collect-only", action="store_true",
        help="run nothing: write the table from runs already in the store, for example after a job array",
    )
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    specifications = build_design_specifications(arguments.design, arguments.seeds)
    if arguments.collect_only:
        runs = collect_stored_runs(specifications, default_result_store())
    else:
        runs = run_guarded_batch(specifications, arguments.workers)
    write_phase_table(runs, phase_directory(PHASE_NAME), arguments.table_name)


if __name__ == "__main__":
    main()
