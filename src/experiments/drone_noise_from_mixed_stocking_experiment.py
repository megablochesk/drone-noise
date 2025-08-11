from common.path_configs import get_mixed_order_dataset_pattern
from common.simulation_configs import simulation_configs
from experiments.simulation_based_experiment_utils import run_experiment_for_each_dataset, run_complex_experiment
from visualiser.plot_noise_level_comparison import plot_single_noise_metric_from_different_dfs

NUMBER_OF_ORDERS = 100000
NUMBER_OF_DRONES = 500

ORDER_DATASETS = {
    f'r{random_ratio}_c{closest_ratio}': get_mixed_order_dataset_pattern(random_ratio, closest_ratio, simulation_configs.orders)
    for random_ratio, closest_ratio in [(ratio, 100 - ratio) for ratio in range(100, 0, -10)]
}


def mixed_random_and_best_stocking_experiment():
    return run_experiment_for_each_dataset(
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


def run_mixed_random_and_best_stocking_experiment(load_saved_results=False):
    run_complex_experiment(
        load_saved_results=load_saved_results,
        result_file_name="mixed_random_and_best_stocking",
        experiment_function=mixed_random_and_best_stocking_experiment,
        visualisation_function=plot_mixed_datasets_noise_maps
    )
