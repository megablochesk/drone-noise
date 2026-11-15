"""The design decided for the revision: Round 4 baseline, 100 m noise cells, 10 s time step; and the entry
point that runs one of its specifications, for a job array on a cluster."""
from dataclasses import replace
from pathlib import Path

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


def stored_run_keys() -> set[str]:
    return {path.stem for path in Path("../results/artifacts/runs").glob("*.json")}


@pytest.mark.parametrize("design_name", ["pilot", "single-landing", "slant-floor", "noise-aware", "paper-figures"])
def test_every_design_reads_the_boundary_on_osgb36_and_adds_runs_beside_the_stored_ones(design_name):
    """The fine grid reads the boundary file on the datum it is written on. Its runs get keys of their own, so the
    stored runs of the published reading stay where they are and the new runs are added."""
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
    assert keys.isdisjoint(stored_run_keys())
