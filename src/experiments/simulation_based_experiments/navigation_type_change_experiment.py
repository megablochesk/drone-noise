from common.enum import NavigationType
from common.path_configs import ORDER_BASE_PATH_FURTHEST, ORDER_BASE_PATH_RANDOM, ORDER_BASE_PATH_CLOSEST
from experiments.config_generator import build_configs_for_datasets_drones_and_navigation_types
from experiments.experiment_executor import run_complex_experiment
from visualiser.navigation_experiment_heatmaps_plotter import plot_heatmaps_per_drone_number_and_navigation_type
from visualiser.navigation_experiment_line_plotter import plot_delivered_orders_lines_facet, \
    plot_average_noise_lines_facet, plot_impacted_population_lines

NAVIGATION_TYPES = [
    NavigationType.STRAIGHT,
    NavigationType.NOISE_A025,
    NavigationType.NOISE_A050,
    NavigationType.NOISE_A075,
    NavigationType.NOISE_A100
]

NUMBER_OF_DRONES_CASES = [1250, 1000, 750, 500, 250, 100]
NUMBER_OF_ORDERS = 100_000

ORDER_DATASETS = {
    'furthest': ORDER_BASE_PATH_FURTHEST,
    'random': ORDER_BASE_PATH_RANDOM,
    'closest': ORDER_BASE_PATH_CLOSEST
}


def generate_configs(drone_landing):
    return build_configs_for_datasets_drones_and_navigation_types(
        datasets=ORDER_DATASETS,
        orders=NUMBER_OF_ORDERS,
        drone_cases=NUMBER_OF_DRONES_CASES,
        navigation_types=NAVIGATION_TYPES,
        drone_landing=drone_landing,
    )


def plot_all_statistics(experiment_results, noise_level_threshold=55):
    plot_average_noise_lines_facet(experiment_results)

    plot_delivered_orders_lines_facet(experiment_results)

    plot_heatmaps_per_drone_number_and_navigation_type(experiment_results)

    plot_impacted_population_lines(experiment_results, threshold=noise_level_threshold)


def run_navigation_type_change_experiment(load_saved_results=True, drone_landing=True):
    result_file_name_suffix = "with_landing" if drone_landing else "no_landing"

    configs_with_names = generate_configs(drone_landing)
    run_complex_experiment(
        load_saved_results=load_saved_results,
        result_file_name=f"navigation_type_change_{result_file_name_suffix}",
        configs_with_names=configs_with_names,
        visualisation_function=plot_all_statistics
    )
