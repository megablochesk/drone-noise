import time

import pandas as pd

from common.file_utils import load_dataframe_from_pickle
from simulation.center import Center
from visualiser.plot_utils import save_figures, plot_figures, add_font_style


def run_complex_experiment(result_file, from_file, experiment_function, post_processing_func=None):
    if from_file:
        print(f"Loading results from file: {result_file}")
        experiment_results = load_dataframe_from_pickle(result_file)
    else:
        print(f"Running experiment and saving results to: {result_file}")
        experiment_results = experiment_function(result_file)

    if post_processing_func:
        print("Running post-processing on experiment results...")
        post_processing_func(experiment_results)

    add_font_style()
    save_figures()
    plot_figures()


def run_atomic_experiment(dataset_name, dataset_path, num_orders, num_drones):
    print(dataset_name, num_drones, num_orders)

    start_time = time.time()

    # Initialize and run the center
    center = Center(num_orders, num_drones, dataset_path)
    center.run_center()

    elapsed_time = time.time() - start_time
    print(f"Time: {elapsed_time} seconds")

    # Gather results
    delivered_orders = center.get_delivered_orders_number()
    noise_impact_df = center.noise_impact
    avg_noise_diff = noise_impact_df['noise_difference'].mean()

    return {
        'dataset_name': dataset_name,
        'num_drones': num_drones,
        'num_orders': num_orders,
        'avg_noise_diff': avg_noise_diff,
        'noise_impact_df': noise_impact_df,
        'delivered_orders_number': delivered_orders,
        'execution_time_seconds': elapsed_time
    }

def process_all_datasets(datasets_description, num_orders, number_of_drones):
    results = []

    for dataset_name, dataset_path in datasets_description:
        result = run_atomic_experiment(dataset_name, dataset_path, num_orders, number_of_drones)
        results.append(result)

    return results

def process_datasets_and_drone_number_combinations(datasets_description, num_orders, drone_number_cases):
    results = []

    for dataset_name, dataset_path in datasets_description:
        for number_of_drones in drone_number_cases:
            result = run_atomic_experiment(dataset_name, dataset_path, num_orders, number_of_drones)
            results.append(result)

    return results

def convert_results_to_dataframe(results):
    return pd.DataFrame(results)



