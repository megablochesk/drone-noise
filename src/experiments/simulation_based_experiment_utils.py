import time

import pandas as pd

from common.file_utils import load_dataframe_from_pickle, save_dataframe_to_pickle
from common.path_configs import get_experiment_results_full_file_path
from common.runtime_configs import runtime_simulation_config
from simulation.simulator import Simulator
from visualiser.plot_utils import finalise_visualisation


def run_complex_experiment(result_file_name, load_saved_results, experiment_function, visualisation_function=None):
    results = _load_or_run_experiment(result_file_name, load_saved_results, experiment_function)

    _visualise_results(results, visualisation_function)


def run_atomic_experiment(dataset_name, dataset_path, num_orders, num_drones):
    print(dataset_name, num_drones, num_orders)

    start_time = time.time()
    simulator = _create_and_run_simulator(dataset_path, num_orders, num_drones)
    elapsed_time = time.time() - start_time

    print(f"Time: {elapsed_time:.2f} seconds")

    return _extract_experiment_results(simulator, dataset_name, num_orders, num_drones, elapsed_time)


def run_experiment_for_each_dataset(datasets_description, order_number, number_of_drones):
    results = []

    for dataset_name, dataset_path in datasets_description:
        result = run_atomic_experiment(dataset_name, dataset_path, order_number, number_of_drones)
        results.append(result)

    return results


def run_experiment_for_each_dataset_and_drone_number(datasets_description, order_number, drone_number_cases):
    results = []

    for dataset_name, dataset_path in datasets_description:
        for number_of_drones in drone_number_cases:
            result = run_atomic_experiment(dataset_name, dataset_path, order_number, number_of_drones)
            results.append(result)

    return results


def _create_and_run_simulator(dataset_path, num_orders, num_drones):
    simulator = Simulator(num_orders, num_drones, dataset_path)
    simulator.run()
    return simulator


def _extract_experiment_results(simulator, dataset_name, num_orders, num_drones, elapsed_time):
    delivered_orders = simulator.delivered_orders_number
    noise_impact_df = simulator.noise_monitor.impact
    avg_noise_difference = noise_impact_df["noise_difference"].mean()

    return {
        'dataset_name': dataset_name,
        'num_drones': num_drones,
        'num_orders': num_orders,
        'avg_noise_diff': avg_noise_difference,
        'noise_impact_df': noise_impact_df,
        'delivered_orders_number': delivered_orders,
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
