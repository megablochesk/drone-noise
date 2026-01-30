from __future__ import annotations

import time
from collections import defaultdict
from enum import Enum
from typing import Any

import pandas as pd

from common.file_utils import load_dataframe_from_pickle, save_dataframe_to_pickle
from common.path_configs import get_experiment_results_full_file_path
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from simulation.simulator import Simulator
from visualiser.plot_utils import finalise_visualisation


def run_complex_experiment(
    result_file_name,
    load_saved_results,
    experiment_function=None,
    visualisation_function=None,
    configs_with_names=None
):
    if configs_with_names is not None:
        def wrapped_experiment():
            return _run_experiments_for_configs(configs_with_names)
        experiment_function = wrapped_experiment

    if experiment_function is None:
        raise ValueError("Either experiment_function or configs_with_names must be provided")

    results = _load_or_run_experiment(result_file_name, load_saved_results, experiment_function)

    _visualise_results(results, visualisation_function)


def _run_experiments_for_configs(configs_with_names):
    grouped = _group_by_navigation_type(configs_with_names)

    results = []
    for nav_name in sorted(grouped.keys()):
        runs = grouped[nav_name]
        print(f"\n=== Running group: navigation_type={nav_name}  (runs={len(runs)}) ===")
        for run_name, config in runs:
            result = _run_atomic_experiment(run_name, config)
            results.append(result)

    return results


def _group_by_navigation_type(configs_with_names):
    groups = defaultdict(list)
    for run_name, config in configs_with_names:
        nav_name = _nav_to_name(config.navigator_type)
        groups[nav_name].append((run_name, config))
    return dict(groups)


def _run_atomic_experiment(run_name: str, config: SimulationConfig):
    start_time = time.time()

    with use_simulation_config(config):
        simulator_after_run = _run_simulation()

        elapsed_time = time.time() - start_time

        return _extract_experiment_results(
            simulator_after_run,
            run_name,
            elapsed_time,
            config
        )


def _run_simulation():
    simulator = Simulator()
    simulator.run()

    return simulator


def _extract_experiment_results(simulator_after_run, run_name, elapsed_time, config):
    dataset_type = _dataset_type_from_run_name(run_name)

    noise_impact_df = simulator_after_run.noise_monitor.impact
    avg_noise_difference = noise_impact_df["noise_difference"].mean()

    return {
        "dataset": dataset_type,
        "dataset_name": dataset_type,
        "run_name": run_name,
        "num_drones": config.number_of_drones,
        "num_orders": config.orders_to_process,
        "navigation_type": _nav_to_name(config.navigator_type),
        "avg_noise_diff": avg_noise_difference,
        "noise_impact_df": noise_impact_df,
        "delivered_orders_number": simulator_after_run.delivered_orders_number,
        "execution_time_seconds": elapsed_time
    }


def _load_or_run_experiment(result_file_name, load_saved_results, experiment_function):
    file_path = get_experiment_results_full_file_path(result_file_name)

    if load_saved_results:
        print(f"Loading results from file: {result_file_name}")
        return _load_results(file_path)

    print(f"Running experiment and saving results to: {result_file_name}")
    return _run_and_store_experiment(experiment_function, file_path)


def _load_results(file_path):
    df = load_dataframe_from_pickle(file_path)
    return _ensure_results_schema(df)


def _run_and_store_experiment(experiment_function, file_path):
    raw_results = experiment_function()
    results_df = _convert_results_to_dataframe(raw_results)
    results_df = _ensure_results_schema(results_df)

    save_dataframe_to_pickle(results_df, file_path)

    return results_df


def _convert_results_to_dataframe(results):
    if isinstance(results, dict):
        return pd.DataFrame([results])
    return pd.DataFrame(results)


def _visualise_results(results, visualisation_function=None):
    if visualisation_function is None:
        return

    print("Running visualisation on experiment results...")
    results = _ensure_results_schema(results)
    visualisation_function(results)

    finalise_visualisation()


def _ensure_results_schema(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()

    if "run_name" not in x.columns and "dataset_name" in x.columns:
        x["run_name"] = x["dataset_name"].astype(str)

    if "dataset_name" in x.columns:
        x["dataset_name"] = x["dataset_name"].map(_dataset_type_from_run_name)

    if "dataset" not in x.columns and "dataset_name" in x.columns:
        x["dataset"] = x["dataset_name"]

    if "navigation_type" in x.columns:
        x["navigation_type"] = x["navigation_type"].map(_nav_to_name)

    return x


def _dataset_type_from_run_name(run_name: Any) -> str:
    s = str(run_name)
    return s.split("_d", 1)[0]


def _nav_to_name(v: Any) -> str:
    if isinstance(v, Enum):
        return v.name
    if hasattr(v, "name"):
        name = getattr(v, "name")
        if isinstance(name, str):
            return name
    return str(v)
