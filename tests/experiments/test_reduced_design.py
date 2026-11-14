"""Designs of Phases 9-12 (brief: fleet {500, 1250} x terminal phases on x 3 seeds) and their comparison tables."""
from dataclasses import replace

import pandas as pd
import pytest

from common.enum import BaselineNoiseMap, OrderDatasetType
from experiments.revision.reduced_design import (
    BASELINE_VARIANT,
    PHASE_CHANGES,
    build_phase_variants,
    compare_variants_with_baseline,
    rank_stockings,
)
from experiments.revision.revision_figures import PHASE_TITLES
from experiments.revision.run_specification import DemandModel, FleetAllocation


def count_runs(variants: dict) -> int:
    return sum(len(specifications) for name, specifications in variants.items() if name != BASELINE_VARIANT)


@pytest.mark.parametrize("phase, expected_variants, expected_runs", [
    ("phase9", 8, 8 * 2 * 2 * 3),
    ("phase10", 6, 6 * 3 * 2 * 3),
    ("phase11", 1, 1 * 3 * 2 * 3),
    ("phase12", 1, 1 * 3 * 2 * 3),
    ("round4_baseline", 1, 1 * 3 * 2 * 3),
])
def test_phase_designs_have_the_runs_the_brief_asks_for(phase, expected_variants, expected_runs):
    """Brief: Phase 9 has 4 new layouts with 5 random draws (8 layouts) for best and random stocking;
    Phase 10 six one-at-a-time values; Phases 11 and 12 one variant each; all on 2 fleets x 3 seeds."""
    variants = build_phase_variants(phase)
    assert len(variants) - 1 == expected_variants
    assert count_runs(variants) == expected_runs
    for specifications in variants.values():
        assert {specification.terminal_phases for specification in specifications} == {True}
        assert {specification.number_of_drones for specification in specifications} == {500, 1250}
        assert {specification.seed for specification in specifications} == {1, 2, 3}


def test_phase_ten_changes_one_parameter_at_a_time():
    """Brief: altitude 60 and 120 m; speed 21 and 30 m/s; landing delay 30 and 120 s."""
    variants = build_phase_variants("phase10")
    changed_values = {
        name: {(s.flight_altitude_m, s.speed_mps, s.landing_delay_s) for s in specifications}
        for name, specifications in variants.items()
    }
    assert changed_values == {
        BASELINE_VARIANT: {(100.0, 27, 60)},
        "altitude_60m": {(60.0, 27, 60)}, "altitude_120m": {(120.0, 27, 60)},
        "speed_21mps": {(100.0, 21, 60)}, "speed_30mps": {(100.0, 30, 60)},
        "landing_delay_30s": {(100.0, 27, 30)}, "landing_delay_120s": {(100.0, 27, 120)},
    }


def test_phases_eleven_and_twelve_change_allocation_and_demand():
    """Brief: Phase 11 allocates drones in proportion to orders; Phase 12 draws demand uniformly by area."""
    proportional = build_phase_variants("phase11")["proportional_allocation"]
    uniform = build_phase_variants("phase12")["uniform_demand_by_area"]
    assert {specification.fleet_allocation for specification in proportional} == {FleetAllocation.PROPORTIONAL_TO_ORDERS}
    assert {specification.demand_model for specification in uniform} == {DemandModel.AREA}
    assert {specification.stocking for specification in uniform} == set(OrderDatasetType)


def test_round_four_variant_changes_the_baseline_map_only():
    """The same runs as the unchanged design, measured against the Round 4 road noise map."""
    variants = build_phase_variants("round4_baseline")
    round4, baseline = variants["round4_road_laeq16h"], variants[BASELINE_VARIANT]
    assert {specification.baseline_noise_map for specification in round4} == {BaselineNoiseMap.ROUND_4_ROAD}
    assert {specification.baseline_noise_map for specification in baseline} == {BaselineNoiseMap.PUBLISHED}
    assert [replace(specification, baseline_noise_map=BaselineNoiseMap.PUBLISHED) for specification in round4] == baseline


def test_every_phase_has_a_figure_title():
    assert set(PHASE_TITLES) == set(PHASE_CHANGES)


def test_phase_nine_uses_best_and_random_stocking_only():
    """Brief: depot layouts for best and random stocking."""
    variants = build_phase_variants("phase9")
    stockings = {specification.stocking for specifications in variants.values() for specification in specifications}
    assert stockings == {OrderDatasetType.CLOSEST, OrderDatasetType.RANDOM}


RUNS = pd.DataFrame({
    "variant": ["baseline"] * 4 + ["faster"] * 4,
    "number_of_drones": [500] * 8,
    "stocking": ["closest", "closest", "random", "random"] * 2,
    "seed": [1, 2, 1, 2] * 2,
    "delivered_orders": [100.0, 120.0, 40.0, 60.0, 110.0, 150.0, 80.0, 180.0],
})


def test_variant_changes_are_paired_by_seed_and_averaged():
    """faster - baseline, closest: 110-100 = 10 and 150-120 = 30 -> mean change 20, mean level 130,
    relative change 130 / 110 - 1 = 18.2 %. random: 40 and 120 -> mean change 80."""
    comparison = compare_variants_with_baseline(RUNS, ["delivered_orders"])
    closest = comparison[(comparison["variant"] == "faster") & (comparison["stocking"] == "closest")].iloc[0]
    random_stocking = comparison[(comparison["variant"] == "faster") & (comparison["stocking"] == "random")].iloc[0]
    assert closest["delivered_orders_mean"] == 130.0
    assert closest["delivered_orders_change"] == 20.0
    assert closest["delivered_orders_relative_change"] == pytest.approx(130.0 / 110.0 - 1.0)
    assert random_stocking["delivered_orders_change"] == 80.0
    assert closest["number_of_seeds"] == 2


def test_stocking_ranking_and_whether_it_changed():
    """Baseline means: closest 110, random 50 -> closest > random. Faster: closest 130, random 130 is a tie
    broken by name, so use a clear case: the ranking string lists stockings from highest to lowest mean."""
    ranking = rank_stockings(compare_variants_with_baseline(RUNS, ["delivered_orders"]), "delivered_orders")
    baseline = ranking[ranking["variant"] == "baseline"].iloc[0]
    assert baseline["stocking_ranking"] == "closest > random"
    assert bool(baseline["ranking_differs_from_baseline"]) is False

    reversed_runs = RUNS.copy()
    reversed_runs.loc[(reversed_runs["variant"] == "faster") & (reversed_runs["stocking"] == "random"), "delivered_orders"] = 500.0
    reversed_ranking = rank_stockings(
        compare_variants_with_baseline(reversed_runs, ["delivered_orders"]), "delivered_orders"
    )
    faster = reversed_ranking[reversed_ranking["variant"] == "faster"].iloc[0]
    assert faster["stocking_ranking"] == "random > closest"
    assert bool(faster["ranking_differs_from_baseline"]) is True


def test_runs_of_a_phase_are_selected_and_labelled_with_their_variant():
    """Hand-built case: a batch table holding runs of two phases; phase 11 keeps only its own 36 runs
    (18 baseline + 18 proportional), each labelled with its variant."""
    from experiments.revision.reduced_design import label_phase_runs
    from experiments.revision.run_specification import build_run_key

    phase11, phase12 = build_phase_variants("phase11"), build_phase_variants("phase12")
    all_keys = {build_run_key(s) for variants in (phase11, phase12) for specs in variants.values() for s in specs}
    batch_table = pd.DataFrame({"run_key": sorted(all_keys), "delivered_orders": range(len(all_keys))})

    labelled = label_phase_runs(batch_table, phase11)

    assert labelled["variant"].value_counts().to_dict() == {"baseline": 18, "proportional_allocation": 18}
    assert labelled.columns.tolist() == ["run_key", "variant", "delivered_orders"]
