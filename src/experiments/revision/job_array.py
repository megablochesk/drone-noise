"""A design as Slurm job arrays: blocks of seeds small enough for the cluster's array size limit, and the tasks
of each block whose runs are not stored yet.

Each output line is one array: its task indices in Slurm's --array syntax, a tab, and the seeds of the block.
The task indices count within the block, which is how run_fine_grid_task numbers them for those seeds.

Usage (from src/):
    python -m experiments.revision.job_array --design paper-figures --seeds $(seq 1 100)              every task
    python -m experiments.revision.job_array --design paper-figures --seeds $(seq 1 100) --missing    unstored tasks
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass

from experiments.revision.batch_runner import default_result_store
from experiments.revision.fine_grid_design import DESIGN_BUILDERS, build_design_specifications
from experiments.revision.result_store import ResultStore, has_result
from experiments.revision.run_specification import build_run_key

# Slurm's default MaxArraySize is 1001, so indices run up to 1000; `scontrol show config` gives the cluster's value.
DEFAULT_MAX_TASKS_PER_ARRAY = 1000


@dataclass(frozen=True)
class ArrayBlock:
    seeds: tuple[int, ...]
    task_indices: tuple[int, ...]


def count_runs_of_seed(design_name: str, seed: int) -> int:
    return len(build_design_specifications(design_name, [seed]))


def split_seeds_into_blocks(design_name: str, seeds: list[int], max_tasks_per_array: int) -> list[tuple[int, ...]]:
    """Consecutive seeds, as many per block as fit; the runs of one seed never span two blocks."""
    blocks: list[tuple[int, ...]] = []
    block: list[int] = []
    tasks_in_block = 0
    for seed in seeds:
        runs_of_seed = count_runs_of_seed(design_name, seed)
        if runs_of_seed > max_tasks_per_array:
            raise ValueError(f"Seed {seed} has {runs_of_seed} runs, more than an array of {max_tasks_per_array} holds")
        if tasks_in_block + runs_of_seed > max_tasks_per_array:
            blocks.append(tuple(block))
            block, tasks_in_block = [], 0
        block.append(seed)
        tasks_in_block += runs_of_seed
    if block:
        blocks.append(tuple(block))
    return blocks


def select_task_indices(design_name: str, seeds: tuple[int, ...], store: ResultStore | None) -> tuple[int, ...]:
    """Every task of the block, or with a store only those whose run it does not hold."""
    specifications = build_design_specifications(design_name, list(seeds))
    return tuple(
        task_index for task_index, specification in enumerate(specifications)
        if store is None or not has_result(store, build_run_key(specification))
    )


def plan_array_blocks(
        design_name: str, seeds: list[int], max_tasks_per_array: int = DEFAULT_MAX_TASKS_PER_ARRAY,
        store: ResultStore | None = None,
) -> list[ArrayBlock]:
    blocks = [
        ArrayBlock(block_seeds, select_task_indices(design_name, block_seeds, store))
        for block_seeds in split_seeds_into_blocks(design_name, seeds, max_tasks_per_array)
    ]
    return [block for block in blocks if block.task_indices]


def format_index_ranges(indices: tuple[int, ...] | list[int]) -> str:
    """Ascending indices as Slurm writes them: runs of consecutive indices become first-last."""
    ranges: list[str] = []
    first = previous = indices[0]
    for index in [*indices[1:], None]:
        if index is not None and index == previous + 1:
            previous = index
            continue
        ranges.append(str(first) if first == previous else f"{first}-{previous}")
        if index is not None:
            first = previous = index
    return ",".join(ranges)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--design", choices=list(DESIGN_BUILDERS), required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--max-array-size", type=int, default=DEFAULT_MAX_TASKS_PER_ARRAY)
    parser.add_argument("--missing", action="store_true", help="only the tasks whose runs are not in the store")
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    store = default_result_store() if arguments.missing else None
    for block in plan_array_blocks(arguments.design, arguments.seeds, arguments.max_array_size, store):
        print(f"{format_index_ranges(block.task_indices)}\t{' '.join(str(seed) for seed in block.seeds)}")


if __name__ == "__main__":
    main()
