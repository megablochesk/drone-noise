"""One specification of a fine-grid design, for a job array on a cluster.

The fast suite is not run per task: run it once before submitting. Each task refuses uncommitted code,
records the commit, and does nothing if its result is already stored.

Usage (from src/):
    python -m experiments.revision.run_fine_grid_task --seeds 1 2 3 --count                              number of tasks
    python -m experiments.revision.run_fine_grid_task --seeds 1 2 3 --task 17                            run task 17
    python -m experiments.revision.run_fine_grid_task --seeds 1 2 3 --design paper-figures --task 17     of another design
"""
import argparse

from experiments.revision.batch_runner import REPOSITORY_ROOT, default_result_store, run_pending_specifications
from experiments.revision.fine_grid_design import DESIGN_BUILDERS, build_design_specifications, select_task_specification
from experiments.revision.run_guard import ensure_clean_working_tree, read_git_hash

ONE_WORKER = 1
DEFAULT_DESIGN = "pilot"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--design", choices=list(DESIGN_BUILDERS), default=DEFAULT_DESIGN)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--count", action="store_true")
    action.add_argument("--task", type=int)
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    specifications = build_design_specifications(arguments.design, arguments.seeds)
    if arguments.count:
        print(len(specifications))
        return

    ensure_clean_working_tree(REPOSITORY_ROOT)
    specification = select_task_specification(specifications, arguments.task)
    run_pending_specifications([specification], default_result_store(), read_git_hash(REPOSITORY_ROOT), ONE_WORKER)


if __name__ == "__main__":
    main()
