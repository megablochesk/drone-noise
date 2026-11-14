"""A published noise-aware result must be reproduced: worst stocking, 100 drones, terminal phases, alpha = 0.25.

The expected numbers are read from the stored result file of the published noise-aware experiments, so the
whole chain is checked: route trees, route planning, simulation and noise.
"""
import pandas as pd
import pytest

from common.enum import NavigationType
from common.path_configs import get_experiment_results_full_file_path, get_single_type_order_dataset_pattern

pytestmark = pytest.mark.slow

NUMBER_OF_ORDERS = 100_000
STOCKING = "furthest"
NUMBER_OF_DRONES = 100
PUBLISHED_RESULTS_FILE = "navigation_type_change_with_landing"
PUBLISHED_NAVIGATION_NAME = "NOISE_A025"
NOISE_TOLERANCE_DB = 1e-9


def load_published_row() -> pd.Series:
    published = pd.read_pickle(get_experiment_results_full_file_path(PUBLISHED_RESULTS_FILE))
    rows = published[
        (published["dataset_name"] == STOCKING) & (published["num_drones"] == NUMBER_OF_DRONES)
        & (published["navigation_type"] == PUBLISHED_NAVIGATION_NAME)
    ]
    assert len(rows) == 1
    return rows.iloc[0]


def run_noise_aware_configuration() -> pd.Series:
    from experiments.config_generator import build_configs_for_datasets_and_drones
    from experiments.experiment_executor import _ensure_results_schema, _run_experiments_for_configs

    datasets = {STOCKING: get_single_type_order_dataset_pattern(STOCKING, NUMBER_OF_ORDERS)}
    configs_with_names = build_configs_for_datasets_and_drones(
        datasets, NUMBER_OF_ORDERS, [NUMBER_OF_DRONES], drone_landing=True
    )
    noise_aware_configs = [
        (name, config.with_overrides(navigator_type=NavigationType.NOISE_A025)) for name, config in configs_with_names
    ]
    return _ensure_results_schema(pd.DataFrame(_run_experiments_for_configs(noise_aware_configs))).iloc[0]


def test_published_noise_aware_result_is_reproduced():
    published, run = load_published_row(), run_noise_aware_configuration()
    assert run["delivered_orders_number"] == published["delivered_orders_number"]
    assert run["avg_noise_diff"] == pytest.approx(published["avg_noise_diff"], abs=NOISE_TOLERANCE_DB)
