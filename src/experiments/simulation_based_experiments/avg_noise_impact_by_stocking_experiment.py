from common.path_configs import ORDER_BASE_PATH_CLOSEST, ORDER_BASE_PATH_RANDOM, ORDER_BASE_PATH_FURTHEST
from experiments.config_generator import generate_configs_for_datasets
from experiments.experiment_executor import run_complex_experiment
from visualiser.plot_noise_level_comparison import plot_noise_level_comparison

NUMBER_OF_DRONES = 100
NUMBER_OF_ORDERS = 100_000

ORDER_DATASETS = {
    'closest': ORDER_BASE_PATH_CLOSEST,
    'random': ORDER_BASE_PATH_RANDOM,
    'furthest': ORDER_BASE_PATH_FURTHEST,
}


def generate_configs():
    return generate_configs_for_datasets(
        ORDER_DATASETS,
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
        vmax=45
    )


def run_avg_noise_for_different_stocking_experiment(load_saved_experiment=False):
    configs_with_names = generate_configs()

    run_complex_experiment(
        load_saved_results=load_saved_experiment,
        result_file_name='avg_noise_for_different_stocking',
        configs_with_names=configs_with_names,
        visualisation_function=plot_noise_comparison_for_different_stocking,
    )
