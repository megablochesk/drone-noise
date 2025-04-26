from common.configuration import (
    ORDER_BASE_PATH_FURTHEST, ORDER_BASE_PATH_RANDOM, ORDER_BASE_PATH_CLOSEST
)
from experiments.simulation_based_experiment_utils import process_all_datasets, run_complex_experiment
from visualiser.plot_noise_level_comparison import plot_noise_level_comparison

NUMBER_OF_DRONES = 100
NUMBER_OF_ORDERS = 100000

ORDER_DATASETS = {
    'closest': ORDER_BASE_PATH_CLOSEST,
    'random': ORDER_BASE_PATH_RANDOM,
    'furthest': ORDER_BASE_PATH_FURTHEST
}


def unlimited_orders_limited_time_experiment():
    return process_all_datasets(
        ORDER_DATASETS.items(),
        NUMBER_OF_ORDERS,
        NUMBER_OF_DRONES
    )


def plot_noise_comparison_for_different_stocking(results_df):
    dataframes = [row['noise_impact_df'] for _, row in results_df.iterrows()]

    plot_noise_level_comparison(
        dataframes,
        metrics=['average_noise', 'average_noise', 'average_noise'],
        titles=['Best Stocking', 'Random Stocking', 'Worst Stocking'],
        file_name='noise_maps',
        vmin=15,
        vmax=45)


def run_avg_noise_for_different_stocking_experiment():
    run_complex_experiment(
        load_saved_results=True,
        result_file_name='noise_maps_df_1',
        experiment_function=run_avg_noise_for_different_stocking_experiment,
        visualisation_function=plot_noise_comparison_for_different_stocking
    )
