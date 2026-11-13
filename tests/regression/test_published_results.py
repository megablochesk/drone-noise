"""Phase 1 regression baseline: the published straight-line results must be reproduced.

Expected values are the numbers printed in the submitted manuscript (10 h, 100,000-order datasets),
supplied in the revision brief; none of them is produced by the code under test in this session.
"""
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd
import pytest

pytestmark = pytest.mark.slow

NUMBER_OF_ORDERS = 100_000
EXPOSURE_THRESHOLD_DB = 55
NOISE_TOLERANCE_DB = 0.01
POPULATION_RELATIVE_TOLERANCE = 0.005


@dataclass(frozen=True)
class PublishedResult:
    stocking: str
    terminal_phases: bool
    number_of_drones: int
    delivered_orders: int
    mean_noise_increase_db: float | None = None
    newly_exposed_population: int | None = None


PUBLISHED_RESULTS = [
    PublishedResult("closest", False, 1250, 74_813, 2.13, 43_975),
    PublishedResult("closest", True, 1250, 50_653, 2.67, 70_156),
    PublishedResult("furthest", True, 1250, 14_013, 2.37, 68_719),
    PublishedResult("closest", False, 100, 8_147),
]


@lru_cache(maxsize=None)
def run_published_configuration(stocking: str, terminal_phases: bool, number_of_drones: int) -> pd.DataFrame:
    from common.path_configs import get_single_type_order_dataset_pattern
    from experiments.config_generator import build_configs_for_datasets_and_drones
    from experiments.experiment_executor import _ensure_results_schema, _run_experiments_for_configs

    datasets = {stocking: get_single_type_order_dataset_pattern(stocking, NUMBER_OF_ORDERS)}
    configs_with_names = build_configs_for_datasets_and_drones(
        datasets, NUMBER_OF_ORDERS, [number_of_drones], drone_landing=terminal_phases
    )
    return _ensure_results_schema(pd.DataFrame(_run_experiments_for_configs(configs_with_names)))


def newly_exposed_population(results: pd.DataFrame) -> float:
    from common.file_utils import load_dataframe_from_pickle
    from common.path_configs import CELL_POPULATION_PATH
    from visualiser.cell_statistics_calculator import calculate_population_impacted_by_noise

    population = load_dataframe_from_pickle(CELL_POPULATION_PATH)
    impacted = calculate_population_impacted_by_noise(results, population, threshold=EXPOSURE_THRESHOLD_DB)
    return impacted["impacted_population"].iloc[0]


def describe(published: PublishedResult) -> str:
    terminal = "terminal" if published.terminal_phases else "no-terminal"
    return f"{published.stocking}-{terminal}-{published.number_of_drones}"


@pytest.mark.parametrize("published", PUBLISHED_RESULTS, ids=describe)
def test_published_result_is_reproduced(published: PublishedResult):
    results = run_published_configuration(published.stocking, published.terminal_phases, published.number_of_drones)
    run = results.iloc[0]

    assert run["delivered_orders_number"] == published.delivered_orders

    if published.mean_noise_increase_db is not None:
        # The manuscript rounds to two decimals, so the comparison is made at that precision.
        assert round(run["avg_noise_diff"], 2) == pytest.approx(published.mean_noise_increase_db, abs=NOISE_TOLERANCE_DB)

    if published.newly_exposed_population is not None:
        assert newly_exposed_population(results) == pytest.approx(
            published.newly_exposed_population, rel=POPULATION_RELATIVE_TOLERANCE
        )
