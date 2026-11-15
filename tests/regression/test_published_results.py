"""Phase 1 regression baseline: the published straight-line results must be reproduced over the whole day.

Expected values are the numbers printed in the submitted manuscript (10 h, 100,000-order datasets),
supplied in the revision brief; none of them is produced by the code under test in this session. Expected
maps are the result pickles saved in April 2026 for the manuscript figures. The first 10 simulated minutes of
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

NOISE_TOLERANCE_DB = 0.01
POPULATION_RELATIVE_TOLERANCE = 0.005
SAVED_PUBLISHED_RESULT_FILES = {False: "drone_number_change", True: "drone_landing_on"}
# Both noise stages sum the same energy, in a different order; over the full day the per-cell maps differ by
# less than 1e-13 dB.
PER_CELL_TOLERANCE_DB = 1e-9


def describe(published: PublishedResult) -> str:
    return describe_configuration(published.configuration)


ENERGY_SUM_RUNNER_CASES = [
    pytest.param(published, id=describe(published), marks=pytest.mark.slow) for published in PUBLISHED_RESULTS
]
PUBLISHED_RUNNER_CASES = [
    pytest.param(published, id=describe(published), marks=pytest.mark.slow)
    for published in PUBLISHED_RESULTS
]


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


def assert_map_is_the_saved_map(current_map: pd.DataFrame, published: PublishedResult):
    saved_map = per_cell_map(load_saved_published_run(published))
    assert current_map.index.equals(saved_map.index)
    assert (current_map - saved_map).abs().max().max() < PER_CELL_TOLERANCE_DB


@pytest.mark.parametrize("published", PUBLISHED_RUNNER_CASES)
def test_published_runner_reproduces_the_published_result_and_map(published: PublishedResult):
    run = run_published_configuration(published.configuration)
    assert_headline_is_published(
        published, run["delivered_orders_number"], run["avg_noise_diff"], newly_exposed_population(run)
    )
    assert_map_is_the_saved_map(per_cell_map(run), published)


@pytest.mark.parametrize("published", ENERGY_SUM_RUNNER_CASES)
def test_energy_sum_runner_reproduces_the_published_result_and_map(published: PublishedResult):
    """Phase 4 acceptance, with the saved per-cell map of the published runner."""
    run = run_published_configuration_on_the_energy_path(published.configuration)
    assert_headline_is_published(
        published, run.row["delivered_orders"], run.row["mean_noise_increase_db"],
        run.row["newly_exposed_population_55db"],
    )

    # The per-step noise stage records a step without drones as 0 dB and the energy sum adds nothing for it,
    # so the two maps are the same only on a day in which every step has drones.
    assert run.row["time_steps_without_drones"] == 0
    assert_map_is_the_saved_map(run.per_cell_map, published)
