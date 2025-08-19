import time

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
    results = []

    for dataset_name, config in configs_with_names:
        result = _run_atomic_experiment(dataset_name, config)
        results.append(result)

    return results


def _run_atomic_experiment(dataset_name, config: SimulationConfig):
    start_time = time.time()

    with use_simulation_config(config):
        simulator_after_run = _run_simulation()

        elapsed_time = time.time() - start_time

        return _extract_experiment_results(
            simulator_after_run,
            dataset_name,
            elapsed_time,
            config
        )


def _run_simulation():
    simulator = Simulator()
    simulator.run()

    return simulator


def _extract_experiment_results(simulator_after_run, dataset_name, elapsed_time, config):
    noise_impact_df = simulator_after_run.noise_monitor.impact
    avg_noise_difference = noise_impact_df["noise_difference"].mean()

    return {
        'dataset_name': dataset_name,
        'num_drones': config.number_of_drones,
        'num_orders': config.orders_to_process,
        'navigation_type': config.navigator_type,
        'avg_noise_diff': avg_noise_difference,
        'noise_impact_df': noise_impact_df,
        'delivered_orders_number': simulator_after_run.delivered_orders_number,
        'execution_time_seconds': elapsed_time
    }


def _load_or_run_experiment(result_file_name, load_saved_results, experiment_function):
    file_path = get_experiment_results_full_file_path(result_file_name)

    if load_saved_results:
        print(f"Loading results from file: {result_file_name}")
        return _load_results(file_path)

    print(f"Running experiment and saving results to: {result_file_name}")
    return _run_and_store_experiment(experiment_function, file_path)


def _load_results(file_path):
    return load_dataframe_from_pickle(file_path)


def _run_and_store_experiment(experiment_function, file_path):
    raw_results = experiment_function()
    results_df = _convert_results_to_dataframe(raw_results)

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
    visualisation_function(results)

    finalise_visualisation()
