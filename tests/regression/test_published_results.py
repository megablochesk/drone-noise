"""Phase 1 regression baseline: the published straight-line results must be reproduced.

Expected values are the numbers printed in the submitted manuscript (10 h, 100,000-order datasets),
supplied in the revision brief; none of them is produced by the code under test in this session.
"""
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


def describe(published: PublishedResult) -> str:
    return describe_configuration(published.configuration)


@pytest.mark.parametrize("published", PUBLISHED_RESULTS, ids=describe)
def test_published_result_is_reproduced(published: PublishedResult):
    run = run_published_configuration(published.configuration)

    assert run["delivered_orders_number"] == published.delivered_orders

    if published.mean_noise_increase_db is not None:
        assert run["avg_noise_diff"] == pytest.approx(published.mean_noise_increase_db, abs=NOISE_TOLERANCE_DB)

    if published.newly_exposed_population is not None:
        assert newly_exposed_population(run) == pytest.approx(
            published.newly_exposed_population, rel=POPULATION_RELATIVE_TOLERANCE
        )


SAVED_PUBLISHED_RESULT_FILES = {False: "drone_number_change", True: "drone_landing_on"}
PER_CELL_TOLERANCE_DB = 1e-9


def load_saved_published_map(published: PublishedResult):
    from common.file_utils import load_dataframe_from_pickle
    from common.path_configs import get_experiment_results_full_file_path

    configuration = published.configuration
    saved_results = load_dataframe_from_pickle(
        get_experiment_results_full_file_path(SAVED_PUBLISHED_RESULT_FILES[configuration.terminal_phases])
    )
    run_name = f"{configuration.stocking}_d{configuration.number_of_drones}"
    return saved_results.loc[saved_results["run_name"] == run_name].iloc[0]


@pytest.mark.parametrize("published", PUBLISHED_RESULTS, ids=describe)
def test_per_cell_maps_match_the_saved_published_run(published: PublishedResult):
    """Characterisation: expected maps are the result pickles saved in April 2026 for the manuscript figures."""
    current_map = per_cell_map(run_published_configuration(published.configuration))
    saved_map = per_cell_map(load_saved_published_map(published))

    assert current_map.index.equals(saved_map.index)
    assert (current_map - saved_map).abs().max().max() < PER_CELL_TOLERANCE_DB


@pytest.mark.parametrize("published", PUBLISHED_RESULTS, ids=describe)
def test_energy_sum_runner_reproduces_the_published_result(published: PublishedResult):
    """Phase 4 acceptance: the revision runner with the energy-sum noise stage against the manuscript numbers."""
    row = run_published_configuration_on_the_energy_path(published.configuration)

    assert row["delivered_orders"] == published.delivered_orders

    if published.mean_noise_increase_db is not None:
        assert row["mean_noise_increase_db"] == pytest.approx(published.mean_noise_increase_db, abs=NOISE_TOLERANCE_DB)

    if published.newly_exposed_population is not None:
        assert row["newly_exposed_population_55db"] == pytest.approx(
            published.newly_exposed_population, rel=POPULATION_RELATIVE_TOLERANCE
        )
