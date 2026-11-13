"""The experimental designs of the revision: which specifications each phase runs."""
from common.enum import OrderDatasetType
from experiments.revision.run_specification import OrderSource, RunSpecification

# Large enough that no actual warehouse runs out of orders at 1,250 drones over 10 h (see REPORT.md, Phase 5).
REVISION_POOL_SIZE = 650_000

PILOT_FLEETS = (1250, 500, 100)
REDUCED_DESIGN_FLEETS = (1250, 500)
REDUCED_DESIGN_SEEDS = (1, 2, 3)
ALL_STOCKINGS = (OrderDatasetType.CLOSEST, OrderDatasetType.RANDOM, OrderDatasetType.FURTHEST)
TERMINAL_MODES = (False, True)

PUBLISHED_HEADLINE_CONFIGURATIONS = (
    (OrderDatasetType.CLOSEST, False, 1250),
    (OrderDatasetType.CLOSEST, True, 1250),
    (OrderDatasetType.FURTHEST, True, 1250),
    (OrderDatasetType.CLOSEST, False, 100),
)


def build_factorial_specifications(
        seeds: list[int], fleets: list[int], stockings: list[OrderDatasetType], terminal_modes: list[bool]
) -> list[RunSpecification]:
    """Full factorial on seeded pools, ordered largest fleet first."""
    return [
        RunSpecification(
            stocking=stocking, number_of_drones=number_of_drones, terminal_phases=terminal_phases,
            seed=seed, pool_size=REVISION_POOL_SIZE,
        )
        for number_of_drones in sorted(fleets, reverse=True)
        for stocking in stockings
        for terminal_phases in terminal_modes
        for seed in seeds
    ]


def build_published_configuration_specifications(order_source: OrderSource, seed: int) -> list[RunSpecification]:
    """The four Phase 1 configurations, on the published 100,000-order files or on a seeded pool."""
    pool_size = RunSpecification.pool_size if order_source is OrderSource.PUBLISHED_DATASET else REVISION_POOL_SIZE
    return [
        RunSpecification(
            stocking=stocking, number_of_drones=number_of_drones, terminal_phases=terminal_phases,
            order_source=order_source, seed=seed, pool_size=pool_size,
        )
        for stocking, terminal_phases, number_of_drones in PUBLISHED_HEADLINE_CONFIGURATIONS
    ]


def build_adaptive_specifications(summary, number_of_drones: int, new_seeds: list[int]) -> list[RunSpecification]:
    """New-seed runs for the configurations of one fleet whose pilot says more seeds are needed.

    `summary` is the replication summary table (one row per configuration and metric); a configuration
    qualifies if any metric requires more replicates than it has.
    """
    fleet_summary = summary[summary["number_of_drones"] == number_of_drones]
    needs_more = fleet_summary[fleet_summary["required_replicates"] > fleet_summary["number_of_replicates"]]
    configurations = needs_more[["stocking", "terminal_phases"]].drop_duplicates()
    return [
        RunSpecification(
            stocking=OrderDatasetType(stocking), number_of_drones=number_of_drones,
            terminal_phases=bool(terminal_phases), seed=seed, pool_size=REVISION_POOL_SIZE,
        )
        for stocking, terminal_phases in configurations.itertuples(index=False)
        for seed in new_seeds
    ]
