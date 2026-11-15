"""Splitting a design into Slurm job arrays of valid size, and finding the tasks whose runs are not stored."""
import numpy as np
import pytest

from experiments.revision.fine_grid_design import build_design_specifications
from experiments.revision.job_array import ArrayBlock, format_index_ranges, plan_array_blocks
from experiments.revision.result_store import ResultStore, save_result
from experiments.revision.run_specification import build_run_key

SEEDS_OF_THE_CLUSTER_EXPERIMENT = list(range(1, 101))
SLURM_DEFAULT_LARGEST_ARRAY_INDEX = 1000


def store_runs(store: ResultStore, specifications):
    for specification in specifications:
        run_key = build_run_key(specification)
        save_result(store, run_key, {"run_key": run_key}, np.zeros(3), np.zeros(2))


@pytest.mark.parametrize(("indices", "expected"), [([4], "4"), ([0, 1, 2, 5, 7, 8, 9], "0-2,5,7-9"), ([3, 5], "3,5")])
def test_task_indices_are_written_as_slurm_ranges(indices, expected):
    assert format_index_ranges(indices) == expected


@pytest.mark.parametrize("design_name", ["pilot", "paper-figures", "single-landing", "slant-floor"])
def test_the_arrays_of_a_design_cover_every_run_once_within_the_array_size_limit(design_name):
    blocks = plan_array_blocks(design_name, SEEDS_OF_THE_CLUSTER_EXPERIMENT, SLURM_DEFAULT_LARGEST_ARRAY_INDEX + 1)

    keys = []
    for block in blocks:
        specifications_of_block = build_design_specifications(design_name, list(block.seeds))
        keys += [build_run_key(specifications_of_block[task_index]) for task_index in block.task_indices]
    assert [seed for block in blocks for seed in block.seeds] == SEEDS_OF_THE_CLUSTER_EXPERIMENT
    assert max(max(block.task_indices) for block in blocks) <= SLURM_DEFAULT_LARGEST_ARRAY_INDEX
    assert len(keys) == len(set(keys))
    assert set(keys) == {
        build_run_key(specification)
        for specification in build_design_specifications(design_name, SEEDS_OF_THE_CLUSTER_EXPERIMENT)
    }


def test_seeds_fill_each_array_as_far_as_the_limit_allows():
    """18 pilot runs per seed: 5 seeds fit in an array of 90 tasks, the sixth starts the next array."""
    blocks = plan_array_blocks("pilot", [1, 2, 3, 4, 5, 6], max_tasks_per_array=90)

    assert blocks == [ArrayBlock((1, 2, 3, 4, 5), tuple(range(90))), ArrayBlock((6,), tuple(range(18)))]


def test_a_seed_with_more_runs_than_an_array_holds_is_refused():
    with pytest.raises(ValueError, match="108 runs"):
        plan_array_blocks("paper-figures", [1], max_tasks_per_array=100)


def test_only_tasks_whose_runs_are_not_stored_are_listed(tmp_path):
    """After an array finishes, the tasks left to resubmit; an array whose runs are all stored is left out."""
    store = ResultStore(tmp_path)
    first_seed = build_design_specifications("pilot", [1])
    second_seed = build_design_specifications("pilot", [2])
    store_runs(store, first_seed)
    store_runs(store, [specification for task_index, specification in enumerate(second_seed) if task_index != 4])

    blocks = plan_array_blocks("pilot", [1, 2, 3], max_tasks_per_array=18, store=store)

    assert blocks == [ArrayBlock((2,), (4,)), ArrayBlock((3,), tuple(range(18)))]
