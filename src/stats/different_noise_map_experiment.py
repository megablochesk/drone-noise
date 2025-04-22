import time

import pandas as pd

from common.configuration import (
    ORDER_BASE_PATH_FURTHEST, ORDER_BASE_PATH_RANDOM, ORDER_BASE_PATH_CLOSEST
)
from common.file_utils import save_dataframe_to_pickle, load_dataframe_from_pickle
from simulation.center import Center
from stats.plot_noise_level_comparison import plot_noise_level_comparison_from_different_dfs
from stats.plot_utils import save_figures, plot_figures, add_font_style

ORDER_DATASETS = {
    'closest': ORDER_BASE_PATH_CLOSEST,
    'random': ORDER_BASE_PATH_RANDOM,
    'furthest': ORDER_BASE_PATH_FURTHEST
}

NUMBER_OF_DRONES = 100
NUMBER_OF_ORDERS = 100000


def unlimited_orders_limited_time_experiment(results_path):
    results = []

    for dataset_name, dataset_path in ORDER_DATASETS.items():
        print(dataset_name, NUMBER_OF_DRONES, NUMBER_OF_ORDERS)

        start_time = time.time()

        center = Center(NUMBER_OF_ORDERS, NUMBER_OF_DRONES, dataset_path)
        center.run_center()

        elapsed_time = time.time() - start_time

        print(f"Time: {elapsed_time} seconds")

        delivered_orders = center.get_delivered_orders_number()
        noise_impact_df = center.noise_impact

        avg_noise_diff = noise_impact_df['noise_difference'].mean()
        results.append({
            'dataset_name': dataset_name,
            'num_drones': NUMBER_OF_DRONES,
            'num_orders': NUMBER_OF_ORDERS,
            'avg_noise_diff': avg_noise_diff,
            'noise_impact_df': noise_impact_df,
            'delivered_orders_number': delivered_orders,
            'execution_time_seconds': elapsed_time
        })

    results_df = pd.DataFrame(results)

    save_dataframe_to_pickle(results_df, results_path)

    return results_df


def plot_noise_maps(results_df):
    filename = 'noise_maps'
    titles = ['Best Stocking', 'Random Stocking', 'Worst Stocking']
    values = ['average_noise', 'average_noise', 'average_noise']
    vmin = 15
    vmax = 45

    dataframes = [row['noise_impact_df'] for _, row in results_df.iterrows()]

    plot_noise_level_comparison_from_different_dfs(dataframes, filename, values, titles, vmin, vmax)


def run_different_dataset_noise_maps():
    results_file = "noise_maps_df_1.pkl"
    from_file = True

    if from_file:
        experiment_results = load_dataframe_from_pickle(results_file)
    else:
        experiment_results = unlimited_orders_limited_time_experiment(results_file)

    add_font_style()

    plot_noise_maps(experiment_results)

    save_figures()

    plot_figures()

