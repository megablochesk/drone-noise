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
    from visualiser.legacy_results import convert_legacy_results

    population = load_dataframe_from_pickle(CELL_POPULATION_PATH)
    runs = convert_legacy_results(results, terminal_phases=True, population=population, threshold_db=EXPOSURE_THRESHOLD_DB)
    return runs["newly_exposed_population"].iloc[0]


def describe(published: PublishedResult) -> str:
    terminal = "terminal" if published.terminal_phases else "no-terminal"
    return f"{published.stocking}-{terminal}-{published.number_of_drones}"


@pytest.mark.parametrize("published", PUBLISHED_RESULTS, ids=describe)
def test_published_result_is_reproduced(published: PublishedResult):
    results = run_published_configuration(published.stocking, published.terminal_phases, published.number_of_drones)
    run = results.iloc[0]

    assert run["delivered_orders_number"] == published.delivered_orders

    if published.mean_noise_increase_db is not None:
        assert run["avg_noise_diff"] == pytest.approx(published.mean_noise_increase_db, abs=NOISE_TOLERANCE_DB)

    if published.newly_exposed_population is not None:
        assert newly_exposed_population(results) == pytest.approx(
            published.newly_exposed_population, rel=POPULATION_RELATIVE_TOLERANCE
        )


SAVED_PUBLISHED_RESULT_FILES = {False: "drone_number_change", True: "drone_landing_on"}
PER_CELL_TOLERANCE_DB = 1e-9


def load_saved_published_map(published: PublishedResult) -> pd.DataFrame:
    from common.file_utils import load_dataframe_from_pickle
    from common.path_configs import get_experiment_results_full_file_path

    saved_results = load_dataframe_from_pickle(
        get_experiment_results_full_file_path(SAVED_PUBLISHED_RESULT_FILES[published.terminal_phases])
    )
    run_name = f"{published.stocking}_d{published.number_of_drones}"
    return saved_results.loc[saved_results["run_name"] == run_name, "noise_impact_df"].iloc[0]


@pytest.mark.parametrize("published", PUBLISHED_RESULTS, ids=describe)
def test_per_cell_maps_match_the_saved_published_run(published: PublishedResult):
    """Characterisation: expected maps are the result pickles saved in April 2026 for the manuscript figures."""
    results = run_published_configuration(published.stocking, published.terminal_phases, published.number_of_drones)
    current_map = results.iloc[0]["noise_impact_df"].set_index(["row", "col"]).sort_index()
    saved_map = load_saved_published_map(published).set_index(["row", "col"]).sort_index()

    assert current_map.index.equals(saved_map.index)
    for column in ["average_noise", "combined_noise", "noise_difference"]:
        assert (current_map[column] - saved_map[column]).abs().max() < PER_CELL_TOLERANCE_DB


@lru_cache(maxsize=None)
def run_published_configuration_on_the_energy_path(stocking: str, terminal_phases: bool, number_of_drones: int) -> dict:
    from common.enum import OrderDatasetType
    from experiments.revision.result_store import ResultStore
    from experiments.revision.run_executor import execute_run
    from experiments.revision.run_specification import OrderSource, RunSpecification

    import tempfile
    from pathlib import Path

    specification = RunSpecification(
        stocking=OrderDatasetType(stocking), number_of_drones=number_of_drones, terminal_phases=terminal_phases,
        order_source=OrderSource.PUBLISHED_DATASET,
    )
    return execute_run(specification, ResultStore(Path(tempfile.mkdtemp())), git_hash="regression-test")


@pytest.mark.parametrize("published", PUBLISHED_RESULTS, ids=describe)
def test_energy_sum_runner_reproduces_the_published_result(published: PublishedResult):
    """Phase 4 acceptance: the revision runner with the energy-sum noise stage against the manuscript numbers."""
    row = run_published_configuration_on_the_energy_path(
        published.stocking, published.terminal_phases, published.number_of_drones
    )

    assert row["delivered_orders"] == published.delivered_orders

    if published.mean_noise_increase_db is not None:
        assert row["mean_noise_increase_db"] == pytest.approx(published.mean_noise_increase_db, abs=NOISE_TOLERANCE_DB)

    if published.newly_exposed_population is not None:
        assert row["newly_exposed_population_55db"] == pytest.approx(
            published.newly_exposed_population, rel=POPULATION_RELATIVE_TOLERANCE
        )
