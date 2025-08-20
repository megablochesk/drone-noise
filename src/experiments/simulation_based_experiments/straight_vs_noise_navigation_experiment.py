from common.enum import NavigationType
from common.path_configs import ORDER_BASE_PATH_FURTHEST, ORDER_BASE_PATH_RANDOM, ORDER_BASE_PATH_CLOSEST
from experiments.config_generator import build_configs_for_datasets_drones_and_navigation_types
from experiments.experiment_executor import run_complex_experiment
from visualiser.cell_statistics_plotter import plot_noise_exceedance_combined, plot_population_impact_combined
from visualiser.general_statistics_plotter import plot_comparison_avg_noise_barchart, plot_comparison_orders_barchart, \
    plot_comparison_execution_time_barchart, plot_delivered_orders_comparison, plot_avg_noise_diff_comparison

NAVIGATION_TYPES = [NavigationType.STRAIGHT, NavigationType.LIGHT_NOISE]

NUMBER_OF_DRONES_CASES = [100, 250, 500, 750, 1000, 1250]
NUMBER_OF_ORDERS = 100_000

ORDER_DATASETS = {
    'furthest': ORDER_BASE_PATH_FURTHEST,
    'random': ORDER_BASE_PATH_RANDOM,
    'closest': ORDER_BASE_PATH_CLOSEST
}


def generate_configs():
    return build_configs_for_datasets_drones_and_navigation_types(
        datasets=ORDER_DATASETS,
        orders=NUMBER_OF_ORDERS,
        drone_cases=NUMBER_OF_DRONES_CASES,
        navigation_types=NAVIGATION_TYPES
    )


def plot_all_statistics(experiment_results):
    plot_comparison_avg_noise_barchart(experiment_results)
    plot_comparison_orders_barchart(experiment_results)
    plot_comparison_execution_time_barchart(experiment_results)

    plot_delivered_orders_comparison(experiment_results)
    plot_avg_noise_diff_comparison(experiment_results)

    for db in range(55, 60, 5):
        plot_noise_exceedance_combined(experiment_results, threshold=db)
        plot_population_impact_combined(experiment_results, threshold=db)


def run_navigation_type_change_experiment(load_saved_results=True):
    configs_with_names = generate_configs()
    run_complex_experiment(
        load_saved_results=load_saved_results,
        result_file_name="navigation_type_change",
        configs_with_names=configs_with_names,
        visualisation_function=plot_all_statistics
    )
