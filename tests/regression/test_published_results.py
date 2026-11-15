"""Phase 1 regression baseline: the published straight-line results must be reproduced over the whole day.

Expected values are the numbers printed in the submitted manuscript (10 h, 100,000-order datasets),
supplied in the revision brief; none of them is produced by the code under test in this session. Expected
maps are the result pickles saved in April 2026 for the manuscript figures. The first 15 simulated minutes of
the same runs are checked in the fast suite (test_published_slices.py).
"""
import pandas as pd
import pytest

from tests.regression.published_runs import (
    PUBLISHED_RESULTS,
    PublishedResult,
    describe as describe_configuration,
    newly_exposed_population,
    per_cell_map,
    run_published_configuration,
    run_published_configuration_on_the_energy_path,
)

pytestmark = pytest.mark.slow

NOISE_TOLERANCE_DB = 0.01
POPULATION_RELATIVE_TOLERANCE = 0.005
SAVED_PUBLISHED_RESULT_FILES = {False: "drone_number_change", True: "drone_landing_on"}
PER_CELL_TOLERANCE_DB = 1e-9


def describe(published: PublishedResult) -> str:
    return describe_configuration(published.configuration)


def load_saved_published_run(published: PublishedResult) -> pd.Series:
    from common.file_utils import load_dataframe_from_pickle
    from common.path_configs import get_experiment_results_full_file_path

    configuration = published.configuration
    saved_results = load_dataframe_from_pickle(
        get_experiment_results_full_file_path(SAVED_PUBLISHED_RESULT_FILES[configuration.terminal_phases])
    )
    run_name = f"{configuration.stocking}_d{configuration.number_of_drones}"
    return saved_results.loc[saved_results["run_name"] == run_name].iloc[0]


def assert_headline_is_published(
        published: PublishedResult, delivered_orders: int, mean_noise_increase_db: float, exposed_population: float
):
    assert delivered_orders == published.delivered_orders

    if published.mean_noise_increase_db is not None:
        assert mean_noise_increase_db == pytest.approx(published.mean_noise_increase_db, abs=NOISE_TOLERANCE_DB)

    if published.newly_exposed_population is not None:
        assert exposed_population == pytest.approx(published.newly_exposed_population, rel=POPULATION_RELATIVE_TOLERANCE)


@pytest.mark.parametrize("published", PUBLISHED_RESULTS, ids=describe)
def test_published_result_and_map_are_reproduced_by_both_runners(published: PublishedResult):
    """The published runner gives the manuscript numbers and the saved per-cell map; the revision runner with
    the energy-sum noise stage gives the manuscript numbers too (Phase 4 acceptance)."""
    run = run_published_configuration(published.configuration)
    assert_headline_is_published(
        published, run["delivered_orders_number"], run["avg_noise_diff"], newly_exposed_population(run)
    )

    current_map, saved_map = per_cell_map(run), per_cell_map(load_saved_published_run(published))
    assert current_map.index.equals(saved_map.index)
    assert (current_map - saved_map).abs().max().max() < PER_CELL_TOLERANCE_DB

    row = run_published_configuration_on_the_energy_path(published.configuration)
    assert_headline_is_published(
        published, row["delivered_orders"], row["mean_noise_increase_db"], row["newly_exposed_population_55db"]
    )
