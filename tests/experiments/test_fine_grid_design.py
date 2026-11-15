"""The design decided for the revision: Round 4 baseline, 100 m noise cells, 10 s time step; and the entry
point that runs one of its specifications, for a job array on a cluster."""
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from common.enum import BaselineNoiseMap, BoundaryDatum, OrderDatasetType
from experiments.revision.fine_grid_design import (
    FINE_BASELINE_NOISE_MAP,
    build_fine_grid_specifications,
    select_task_specification,
)
from experiments.revision.revision_design import REVISION_POOL_SIZE
from experiments.revision.run_specification import build_run_key


def test_one_seed_has_the_eighteen_pilot_configurations_on_the_fine_grid():
    """3 fleets x 3 stockings x 2 terminal modes, every run with 100 m cells, a 10 s step and Round 4."""
    specifications = build_fine_grid_specifications(seeds=[7])
    assert len(specifications) == len(set(specifications)) == 18
    assert {specification.number_of_drones for specification in specifications} == {1250, 500, 100}
    assert {specification.stocking for specification in specifications} == set(OrderDatasetType)
    assert {specification.terminal_phases for specification in specifications} == {False, True}
    assert {(s.noise_cell_m, s.time_step_s, s.seed, s.pool_size) for s in specifications} == {(100, 10, 7, REVISION_POOL_SIZE)}
    assert {specification.baseline_noise_map for specification in specifications} == {FINE_BASELINE_NOISE_MAP}
    assert FINE_BASELINE_NOISE_MAP in (BaselineNoiseMap.ROUND_4_ROAD, BaselineNoiseMap.ROUND_4_ROAD_ENERGY)


def test_seeds_multiply_the_design_and_the_largest_fleet_comes_first():
    specifications = build_fine_grid_specifications(seeds=[1, 2, 3])
    assert len({build_run_key(specification) for specification in specifications}) == 54
    fleets = [specification.number_of_drones for specification in specifications]
    assert fleets == sorted(fleets, reverse=True)


def test_task_number_selects_one_specification_of_the_design():
    """Job arrays count from zero; the order of the design is the order of the tasks."""
    specifications = build_fine_grid_specifications(seeds=[1, 2])
    assert select_task_specification(specifications, 0) == specifications[0]
    assert select_task_specification(specifications, 35) == specifications[35]


@pytest.mark.parametrize("task_index", [-1, 36])
def test_task_number_outside_the_design_is_an_error(task_index):
    with pytest.raises(IndexError, match="36 specifications"):
        select_task_specification(build_fine_grid_specifications(seeds=[1, 2]), task_index)


def test_every_design_is_reachable_by_name():
    """The same names select a design on one machine and in a cluster job array."""
    from experiments.revision.fine_grid_design import (
        DESIGN_BUILDERS,
        build_design_specifications,
        build_noise_aware_specifications,
        build_paper_figure_specifications,
        build_single_landing_specifications,
        build_slant_floor_specifications,
    )

    assert list(DESIGN_BUILDERS) == ["pilot", "single-landing", "slant-floor", "noise-aware", "paper-figures"]
    assert build_design_specifications("pilot", [1, 2]) == build_fine_grid_specifications([1, 2])
    assert build_design_specifications("single-landing", [3]) == build_single_landing_specifications([3])
    assert build_design_specifications("slant-floor", [3]) == build_slant_floor_specifications([3])
    assert build_design_specifications("noise-aware", [3]) == build_noise_aware_specifications([3])
    assert build_design_specifications("paper-figures", [3]) == build_paper_figure_specifications([3])


def test_an_unknown_design_is_refused_with_the_known_names():
    from experiments.revision.fine_grid_design import build_design_specifications

    with pytest.raises(ValueError, match="pilot, single-landing"):
        build_design_specifications("everything", [1])


def read_boundary_datums_of_stored_runs(keys: set[str]) -> set[str]:
    stored_paths = (Path("../results/artifacts/runs") / f"{key}.json" for key in keys)
    return {json.loads(path.read_text())["boundary_datum"] for path in stored_paths if path.exists()}


@pytest.mark.parametrize("design_name", ["pilot", "single-landing", "slant-floor", "noise-aware", "paper-figures"])
def test_every_design_reads_the_boundary_on_osgb36_and_adds_runs_beside_the_stored_ones(design_name):
    """The fine grid reads the boundary file on the datum it is written on. Its runs get keys of their own, so the
    stored runs of the published reading stay where they are: no run stored under a key of the design reads the
    boundary on another datum."""
    from experiments.revision.fine_grid_design import FINE_BOUNDARY_DATUM, build_design_specifications

    specifications = build_design_specifications(design_name, [1, 2, 3])
    keys = {build_run_key(specification) for specification in specifications}
    published_reading_keys = {
        build_run_key(replace(specification, boundary_datum=BoundaryDatum.WGS84)) for specification in specifications
    }

    assert FINE_BOUNDARY_DATUM is BoundaryDatum.OSGB36
    assert {specification.boundary_datum for specification in specifications} == {BoundaryDatum.OSGB36}
    assert len(keys) == len(published_reading_keys) == len(specifications)
    assert keys.isdisjoint(published_reading_keys)
    assert read_boundary_datums_of_stored_runs(keys) <= {BoundaryDatum.OSGB36.value}


SEEDS_OF_THE_CLUSTER_EXPERIMENT = list(range(1, 101))
DESIGN_NAMES = ["pilot", "single-landing", "slant-floor", "noise-aware", "paper-figures"]


@pytest.mark.parametrize("design_name", DESIGN_NAMES)
def test_the_tasks_of_a_hundred_seed_array_name_every_run_exactly_once(design_name):
    """Task i runs specification i: the indices from zero to the count cover the design without repeats, and the
    first index past it fails loudly instead of running something else."""
    from experiments.revision.fine_grid_design import build_design_specifications

    specifications = build_design_specifications(design_name, SEEDS_OF_THE_CLUSTER_EXPERIMENT)
    task_keys = [
        build_run_key(select_task_specification(specifications, task_index)) for task_index in range(len(specifications))
    ]

    assert len(set(task_keys)) == len(task_keys)
    assert set(task_keys) == {build_run_key(specification) for specification in specifications}
    with pytest.raises(IndexError):
        select_task_specification(specifications, len(specifications))


def list_task_keys_in_a_new_process(hash_seed: str) -> str:
    program = (
        "from experiments.revision.fine_grid_design import DESIGN_BUILDERS, build_design_specifications\n"
        "from experiments.revision.run_specification import build_run_key\n"
        "for name in DESIGN_BUILDERS:\n"
        "    print(name, *(build_run_key(s) for s in build_design_specifications(name, [1, 2, 3])))\n"
    )
    environment = {**os.environ, "PYTHONHASHSEED": hash_seed}
    completed = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True, check=True, env=environment, cwd=Path.cwd()
    )
    return completed.stdout


def test_every_task_process_numbers_the_design_alike():
    """Each array task is a process of its own, with its own hash seed: the order of the design must not depend
    on it, or two tasks could run the same specification and leave another out."""
    assert list_task_keys_in_a_new_process("1") == list_task_keys_in_a_new_process("2")


def test_a_task_whose_run_is_stored_runs_nothing(tmp_path, monkeypatch):
    """A resubmitted task finds its run in the store and finishes without simulating."""
    import experiments.revision.batch_runner as batch_runner
    from experiments.revision.fine_grid_design import build_design_specifications
    from experiments.revision.result_store import ResultStore, save_result

    def refuse_to_run(*arguments):
        raise AssertionError("a stored run was executed again")

    monkeypatch.setattr(batch_runner, "execute_run", refuse_to_run)
    store = ResultStore(tmp_path)
    specification = build_design_specifications("pilot", [1])[0]
    run_key = build_run_key(specification)
    save_result(store, run_key, {"run_key": run_key}, np.zeros(3), np.zeros(2))

    assert batch_runner.run_pending_specifications([specification], store, "0" * 40, number_of_workers=1) == []
