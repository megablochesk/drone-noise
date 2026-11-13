from common.enum import OrderDatasetType
from experiments.revision.revision_design import (
    PUBLISHED_HEADLINE_CONFIGURATIONS,
    REVISION_POOL_SIZE,
    build_factorial_specifications,
    build_published_configuration_specifications,
)
from experiments.revision.run_specification import OrderSource


def test_pilot_design_has_ninety_runs():
    """Brief: 5 seeds x fleet {1250, 500, 100} x 3 stockings x 2 terminal modes = 90 runs."""
    specifications = build_factorial_specifications(
        seeds=[1, 2, 3, 4, 5], fleets=[1250, 500, 100], stockings=list(OrderDatasetType), terminal_modes=[False, True]
    )
    assert len(specifications) == 90
    assert len(set(specifications)) == 90
    assert {specification.pool_size for specification in specifications} == {REVISION_POOL_SIZE}
    assert {specification.order_source for specification in specifications} == {OrderSource.SEEDED_POOL}


def test_largest_fleet_comes_first():
    """Brief: largest fleet first, so an interrupted batch has the most informative runs."""
    specifications = build_factorial_specifications(
        seeds=[1, 2], fleets=[100, 1250, 500], stockings=[OrderDatasetType.CLOSEST], terminal_modes=[False]
    )
    assert [specification.number_of_drones for specification in specifications] == [1250, 1250, 500, 500, 100, 100]


def test_published_headline_configurations_are_the_four_of_phase_one():
    """Brief, Phase 1: best/no terminal/1250, best/terminal/1250, worst/terminal/1250, best/no terminal/100."""
    assert PUBLISHED_HEADLINE_CONFIGURATIONS == (
        (OrderDatasetType.CLOSEST, False, 1250),
        (OrderDatasetType.CLOSEST, True, 1250),
        (OrderDatasetType.FURTHEST, True, 1250),
        (OrderDatasetType.CLOSEST, False, 100),
    )
    published = build_published_configuration_specifications(OrderSource.PUBLISHED_DATASET, seed=0)
    assert [(s.stocking, s.terminal_phases, s.number_of_drones) for s in published] == \
           list(PUBLISHED_HEADLINE_CONFIGURATIONS)
    assert {specification.order_source for specification in published} == {OrderSource.PUBLISHED_DATASET}


def test_adaptive_block_adds_seeds_only_to_configurations_that_need_them():
    """Hand-built summary at 1,250 drones with 5 seeds each: closest/terminal needs 9 for one metric (more
    than 5 -> gets the new seeds), random/cruise needs at most 4 (enough already). Other fleets are ignored."""
    import pandas as pd

    from experiments.revision.revision_design import build_adaptive_specifications

    summary = pd.DataFrame({
        "number_of_drones": [1250, 1250, 1250, 1250, 500],
        "terminal_phases": [True, True, False, False, True],
        "stocking": ["closest", "closest", "random", "random", "closest"],
        "metric": ["delivered_orders", "newly_exposed_population_55db"] * 2 + ["newly_exposed_population_55db"],
        "number_of_replicates": [5, 5, 5, 5, 5],
        "required_replicates": [2, 9, 2, 4, 41],
    })
    specifications = build_adaptive_specifications(summary, number_of_drones=1250, new_seeds=[6, 7])

    assert [(s.stocking, s.terminal_phases, s.number_of_drones, s.seed) for s in specifications] == [
        (OrderDatasetType.CLOSEST, True, 1250, 6), (OrderDatasetType.CLOSEST, True, 1250, 7),
    ]
