import pandas as pd

from common.path_configs import ORDER_BASE_PATH_FURTHEST, ORDER_BASE_PATH_RANDOM, ORDER_BASE_PATH_CLOSEST
from experiments.config_generator import build_configs_for_datasets_and_drones
from census_analysis.cell_datasets import load_cell_population
from experiments.experiment_executor import run_complex_experiment
from visualiser.paper_experiment_figures import draw_fleet_experiment_figures

NUMBER_OF_DRONES_CASES = [1250, 1000, 750, 500, 250, 100]
NUMBER_OF_ORDERS = 100_000

ORDER_DATASETS = {
    "furthest": ORDER_BASE_PATH_FURTHEST,
    "random": ORDER_BASE_PATH_RANDOM,
    "closest": ORDER_BASE_PATH_CLOSEST,
}


def generate_configs():
    return build_configs_for_datasets_and_drones(
        ORDER_DATASETS,
        NUMBER_OF_ORDERS,
        NUMBER_OF_DRONES_CASES
    )


def plot_all_statistics(experiment_results, figure_directory):
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    print(experiment_results[['dataset_name', 'run_name', 'num_drones',
                              'avg_noise_diff',
                              'delivered_orders_number']])

    draw_fleet_experiment_figures(experiment_results, figure_directory, load_cell_population(), name_suffix="")


def run_drone_number_change_experiment(load_saved_results=False):
    run_complex_experiment(
        load_saved_results=load_saved_results,
        result_file_name="drone_number_change",
        configs_with_names=generate_configs(),
        visualisation_function=plot_all_statistics
    )
