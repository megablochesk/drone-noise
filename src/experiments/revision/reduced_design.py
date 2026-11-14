"""Phases 9-12: variants of the reduced design (fleet {500, 1250}, terminal phases, 3 seeds) and their tables."""
from dataclasses import replace

import pandas as pd

from common.enum import BaselineNoiseMap, OrderDatasetType
from depots.depot_layouts import POPULATION_KMEANS_LAYOUT, RANDOM_DRAW_LAYOUTS, RING_LAYOUT, SINGLE_HUB_LAYOUT
from experiments.revision.revision_design import (
    ALL_STOCKINGS,
    REDUCED_DESIGN_FLEETS,
    REDUCED_DESIGN_SEEDS,
    build_factorial_specifications,
)
from experiments.revision.run_specification import DemandModel, FleetAllocation, RunSpecification, build_run_key

BASELINE_VARIANT = "baseline"
LAYOUT_STOCKINGS = (OrderDatasetType.CLOSEST, OrderDatasetType.RANDOM)
STYLISED_LAYOUTS = (SINGLE_HUB_LAYOUT, RING_LAYOUT, POPULATION_KMEANS_LAYOUT, *RANDOM_DRAW_LAYOUTS)
ONE_AT_A_TIME_CHANGES = {
    "altitude_60m": {"flight_altitude_m": 60.0},
    "altitude_120m": {"flight_altitude_m": 120.0},
    "speed_21mps": {"speed_mps": 21},
    "speed_30mps": {"speed_mps": 30},
    "landing_delay_30s": {"landing_delay_s": 30},
    "landing_delay_120s": {"landing_delay_s": 120},
}
PHASE_CHANGES = {
    "phase9": {layout_name: {"depot_layout": layout_name} for layout_name in STYLISED_LAYOUTS},
    "phase10": ONE_AT_A_TIME_CHANGES,
    "phase11": {"proportional_allocation": {"fleet_allocation": FleetAllocation.PROPORTIONAL_TO_ORDERS}},
    "phase12": {"uniform_demand_by_area": {"demand_model": DemandModel.AREA}},
    "round4_baseline": {BaselineNoiseMap.ROUND_4_ROAD.value: {"baseline_noise_map": BaselineNoiseMap.ROUND_4_ROAD}},
}


def build_baseline_specifications(stockings: tuple[OrderDatasetType, ...]) -> list[RunSpecification]:
    return build_factorial_specifications(
        list(REDUCED_DESIGN_SEEDS), list(REDUCED_DESIGN_FLEETS), list(stockings), terminal_modes=[True]
    )


def build_phase_variants(phase_name: str) -> dict[str, list[RunSpecification]]:
    """Variant name -> specifications; the baseline is the unchanged reduced design for the same stockings."""
    stockings = LAYOUT_STOCKINGS if phase_name == "phase9" else ALL_STOCKINGS
    baseline = build_baseline_specifications(stockings)
    variants = {BASELINE_VARIANT: baseline}
    for variant_name, changes in PHASE_CHANGES[phase_name].items():
        variants[variant_name] = [replace(specification, **changes) for specification in baseline]
    return variants


def compare_variants_with_baseline(runs: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    """Per variant, fleet and stocking: mean over seeds, and the mean seed-paired change from the baseline."""
    pairing = ["number_of_drones", "stocking", "seed"]
    baseline = runs.loc[runs["variant"] == BASELINE_VARIANT, [*pairing, *metrics]]
    paired = runs.merge(baseline, on=pairing, suffixes=("", "_baseline"))
    for metric in metrics:
        paired[f"{metric}_change"] = paired[metric] - paired[f"{metric}_baseline"]

    grouped = paired.groupby(["variant", "number_of_drones", "stocking"], sort=False)
    means = grouped[[*metrics, *[f"{metric}_baseline" for metric in metrics]]].mean()
    comparison = pd.concat([grouped.size().rename("number_of_seeds"), grouped[[f"{m}_change" for m in metrics]].mean()], axis=1)
    for metric in metrics:
        comparison[f"{metric}_mean"] = means[metric]
        comparison[f"{metric}_relative_change"] = means[metric] / means[f"{metric}_baseline"] - 1.0
    return comparison.reset_index()


def describe_ranking(group: pd.DataFrame, mean_column: str) -> str:
    return " > ".join(group.sort_values(mean_column, ascending=False)["stocking"])


def rank_stockings(comparison: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Stockings ordered from highest to lowest mean of the metric, per variant and fleet."""
    mean_column = f"{metric}_mean"
    rankings = (
        comparison.groupby(["variant", "number_of_drones"], sort=False)
        .apply(lambda group: describe_ranking(group, mean_column), include_groups=False)
        .rename("stocking_ranking").reset_index()
    )
    baseline = rankings.loc[rankings["variant"] == BASELINE_VARIANT, ["number_of_drones", "stocking_ranking"]]
    rankings = rankings.merge(baseline, on="number_of_drones", suffixes=("", "_baseline"))
    rankings["ranking_differs_from_baseline"] = rankings["stocking_ranking"] != rankings["stocking_ranking_baseline"]
    return rankings.assign(metric=metric)


def label_phase_runs(batch_runs: pd.DataFrame, variants: dict[str, list[RunSpecification]]) -> pd.DataFrame:
    """The rows of a batch table that belong to one phase, with a `variant` column after the run key."""
    variant_by_run_key = {
        build_run_key(specification): variant_name
        for variant_name, specifications in variants.items() for specification in specifications
    }
    phase_runs = batch_runs[batch_runs["run_key"].isin(variant_by_run_key)].drop_duplicates(subset="run_key").copy()
    phase_runs.insert(1, "variant", phase_runs["run_key"].map(variant_by_run_key))
    return phase_runs.reset_index(drop=True)
