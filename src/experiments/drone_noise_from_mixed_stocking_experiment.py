from common.configuration import get_mixed_order_dataset_pattern
from experiments.simulation_based_experiment_utils import process_all_datasets, run_complex_experiment
from visualiser.plot_noise_level_comparison import plot_single_noise_metric_from_different_dfs

NUMBER_OF_ORDERS = 100000
NUMBER_OF_DRONES = 500

ORDER_DATASETS = {
    f'r{random_ratio}_c{closest_ratio}': get_mixed_order_dataset_pattern(random_ratio, closest_ratio)
    for random_ratio, closest_ratio in [(ratio, 100 - ratio) for ratio in range(100, 0, -10)]
}


def unlimited_orders_limited_time_mixed_datasets_experiment():
    return process_all_datasets(
        ORDER_DATASETS.items(),
        NUMBER_OF_ORDERS,
        NUMBER_OF_DRONES
    )


def plot_mixed_datasets_noise_maps(results_df):
    dataframes = [row['noise_impact_df'] for _, row in results_df.iterrows()]

    plot_single_noise_metric_from_different_dfs(
        dataframes,
        metric='average_noise',
        vmin=25,
        vmax=50,
        filename='mixed_datasets_noise_maps')


def run_drone_number_change_experiment():
    run_complex_experiment(
        load_saved_results=True,
        result_file_name="results 72000 mixed",
        experiment_function=unlimited_orders_limited_time_mixed_datasets_experiment,
        visualisation_function=plot_mixed_datasets_noise_maps
    )
