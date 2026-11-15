"""A published noise-aware result must be reproduced: worst stocking, 100 drones, terminal phases, alpha = 0.25.

The expected numbers are read from the stored result file of the published noise-aware experiments, so the
whole chain is checked: route trees, route planning, simulation and noise.
"""
import pandas as pd
import pytest

from common.path_configs import get_experiment_results_full_file_path
from tests.regression.published_runs import PUBLISHED_NOISE_AWARE_CONFIGURATION, run_published_configuration

pytestmark = pytest.mark.slow

PUBLISHED_RESULTS_FILE = "navigation_type_change_with_landing"
PUBLISHED_NAVIGATION_NAME = "NOISE_A025"
NOISE_TOLERANCE_DB = 1e-9


def load_published_row() -> pd.Series:
    published = pd.read_pickle(get_experiment_results_full_file_path(PUBLISHED_RESULTS_FILE))
    rows = published[
        (published["dataset_name"] == PUBLISHED_NOISE_AWARE_CONFIGURATION.stocking)
        & (published["num_drones"] == PUBLISHED_NOISE_AWARE_CONFIGURATION.number_of_drones)
        & (published["navigation_type"] == PUBLISHED_NAVIGATION_NAME)
    ]
    assert len(rows) == 1
    return rows.iloc[0]


def test_published_noise_aware_result_is_reproduced():
    published, run = load_published_row(), run_published_configuration(PUBLISHED_NOISE_AWARE_CONFIGURATION)
    assert run["delivered_orders_number"] == published["delivered_orders_number"]
    assert run["avg_noise_diff"] == pytest.approx(published["avg_noise_diff"], abs=NOISE_TOLERANCE_DB)
