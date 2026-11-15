"""The published configurations and the two code paths that run them, for the whole published day or a part.

The full-day regression tests, the short-period tests and the generator of the short-period reference slices
all run the model through these functions, so a reference slice comes from the code the full-day tests verify.
"""
import json
import tempfile
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

import pandas as pd

from common.enum import NavigationType, OrderDatasetType
from common.model_configs import model_config
from common.simulation_configs import DEFAULT_SIMULATION_CONFIGS
from experiments.revision.run_specification import PUBLISHED_SIMULATION_END_S

NUMBER_OF_ORDERS = 100_000
EXPOSURE_THRESHOLD_DB = 55
SECONDS_PER_MINUTE = 60
SLICE_DURATION_S = 10 * SECONDS_PER_MINUTE
SLICE_SIMULATION_END_S = model_config.time.start_s + SLICE_DURATION_S
MAP_KEY = ["row", "col"]
MAP_COLUMNS = ["average_noise", "combined_noise", "noise_difference"]
REFERENCE_SLICES_DIRECTORY = Path(__file__).resolve().parent / "data" / "published_slices"


@dataclass(frozen=True)
class PublishedConfiguration:
    stocking: str
    terminal_phases: bool
    number_of_drones: int
    navigation: NavigationType = NavigationType.STRAIGHT


@dataclass(frozen=True)
class PublishedResult:
    configuration: PublishedConfiguration
    delivered_orders: int
    mean_noise_increase_db: float | None = None
    newly_exposed_population: int | None = None


# Numbers printed in the submitted manuscript (10 h, 100,000-order datasets).
PUBLISHED_RESULTS = [
    PublishedResult(PublishedConfiguration("closest", False, 1250), 74_813, 2.13, 43_975),
    PublishedResult(PublishedConfiguration("closest", True, 1250), 50_653, 2.67, 70_156),
    PublishedResult(PublishedConfiguration("furthest", True, 1250), 14_013, 2.37, 68_719),
    PublishedResult(PublishedConfiguration("closest", False, 100), 8_147),
]
PUBLISHED_STRAIGHT_LINE_CONFIGURATIONS = [published.configuration for published in PUBLISHED_RESULTS]
# The published noise-aware run: worst stocking, 100 drones, terminal phases, alpha = 0.25.
PUBLISHED_NOISE_AWARE_CONFIGURATION = PublishedConfiguration("furthest", True, 100, NavigationType.NOISE_A025)


def describe(configuration: PublishedConfiguration) -> str:
    terminal = "terminal" if configuration.terminal_phases else "no-terminal"
    navigation = "" if configuration.navigation is NavigationType.STRAIGHT else f"-{configuration.navigation.name.lower()}"
    return f"{configuration.stocking}-{terminal}-{configuration.number_of_drones}{navigation}"


def build_base_config(simulation_end_s: int):
    return DEFAULT_SIMULATION_CONFIGS.with_overrides(
        model=replace(model_config, time=replace(model_config.time, end_s=simulation_end_s))
    )


@lru_cache(maxsize=None)
def run_published_configuration(
        configuration: PublishedConfiguration, simulation_end_s: int = PUBLISHED_SIMULATION_END_S
) -> pd.Series:
    """The published experiment runner: one run of the 500 m model, ending at the given time of day."""
    from common.path_configs import get_single_type_order_dataset_pattern
    from experiments.config_generator import build_configs_for_datasets_and_drones
    from experiments.experiment_executor import _ensure_results_schema, _run_experiments_for_configs

    datasets = {configuration.stocking: get_single_type_order_dataset_pattern(configuration.stocking, NUMBER_OF_ORDERS)}
    configs_with_names = build_configs_for_datasets_and_drones(
        datasets, NUMBER_OF_ORDERS, [configuration.number_of_drones], drone_landing=configuration.terminal_phases,
        base_config=build_base_config(simulation_end_s),
    )
    configs_with_names = [
        (name, config.with_overrides(navigator_type=configuration.navigation)) for name, config in configs_with_names
    ]
    return _ensure_results_schema(pd.DataFrame(_run_experiments_for_configs(configs_with_names))).iloc[0]


def newly_exposed_population(run: pd.Series) -> float:
    from common.file_utils import load_dataframe_from_pickle
    from common.path_configs import CELL_POPULATION_PATH
    from visualiser.legacy_results import convert_legacy_results

    population = load_dataframe_from_pickle(CELL_POPULATION_PATH)
    runs = convert_legacy_results(
        run.to_frame().T, terminal_phases=True, population=population, threshold_db=EXPOSURE_THRESHOLD_DB
    )
    return runs["newly_exposed_population"].iloc[0]


def per_cell_map(run: pd.Series) -> pd.DataFrame:
    return run["noise_impact_df"].set_index(MAP_KEY).sort_index()[MAP_COLUMNS]


@lru_cache(maxsize=None)
def run_published_configuration_on_the_energy_path(
        configuration: PublishedConfiguration, simulation_end_s: int = PUBLISHED_SIMULATION_END_S
) -> dict:
    """The revision runner with the energy-sum noise stage, on the published order dataset."""
    from experiments.revision.result_store import ResultStore
    from experiments.revision.run_executor import execute_run
    from experiments.revision.run_specification import OrderSource, RunSpecification

    specification = RunSpecification(
        stocking=OrderDatasetType(configuration.stocking), number_of_drones=configuration.number_of_drones,
        terminal_phases=configuration.terminal_phases, order_source=OrderSource.PUBLISHED_DATASET,
        navigation=configuration.navigation, simulation_end_s=simulation_end_s,
    )
    with tempfile.TemporaryDirectory() as store_directory:
        return execute_run(specification, ResultStore(Path(store_directory)), git_hash="regression-test")


def summarise_published_runner(configuration: PublishedConfiguration, simulation_end_s: int) -> dict:
    run = run_published_configuration(configuration, simulation_end_s)
    return {
        "delivered_orders": int(run["delivered_orders_number"]),
        "mean_noise_increase_db": float(run["avg_noise_diff"]),
        "newly_exposed_population": float(newly_exposed_population(run)),
    }


def summarise_energy_sum_runner(configuration: PublishedConfiguration, simulation_end_s: int) -> dict:
    row = run_published_configuration_on_the_energy_path(configuration, simulation_end_s)
    return {
        "delivered_orders": int(row["delivered_orders"]),
        "mean_noise_increase_db": float(row["mean_noise_increase_db"]),
        "newly_exposed_population": float(row["newly_exposed_population_55db"]),
        "assigned_orders": int(row["assigned_orders"]),
    }


def headline_path(configuration: PublishedConfiguration) -> Path:
    return REFERENCE_SLICES_DIRECTORY / f"{describe(configuration)}.json"


def map_path(configuration: PublishedConfiguration) -> Path:
    return REFERENCE_SLICES_DIRECTORY / f"{describe(configuration)}_map.csv"


def load_reference_headline(configuration: PublishedConfiguration) -> dict:
    return json.loads(headline_path(configuration).read_text())


def load_reference_map(configuration: PublishedConfiguration) -> pd.DataFrame:
    return pd.read_csv(map_path(configuration)).set_index(MAP_KEY).sort_index()[MAP_COLUMNS]
