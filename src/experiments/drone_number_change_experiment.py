from common.configuration import (
    ORDER_BASE_PATH_FURTHEST, ORDER_BASE_PATH_RANDOM, ORDER_BASE_PATH_CLOSEST
)
from experiments.simulation_based_experiment_utils import (
    run_experiment_for_each_dataset_and_drone_number,
    run_complex_experiment
)

from visualiser.plotter import (
    plot_avg_noise_barchart, plot_delivered_orders_barchart,
    analyze_and_plot_noise_increase,
    analyze_and_plot_population_impact, plot_execution_time_barchart
)

NUMBER_OF_DRONES_CASES = [100, 250, 500, 750, 1000, 1250]
NUMBER_OF_ORDERS = 100000

ORDER_DATASETS = {
    'furthest': ORDER_BASE_PATH_FURTHEST,
    'random': ORDER_BASE_PATH_RANDOM,
    'closest': ORDER_BASE_PATH_CLOSEST
}


def drone_number_change_experiment():
    return run_experiment_for_each_dataset_and_drone_number(
        ORDER_DATASETS.items(),
        NUMBER_OF_ORDERS,
        NUMBER_OF_DRONES_CASES
    )


def plot_all_statistics(experiment_results):
    # plot_cells_impacted_by_noise(experiment_results, 55)

    plot_execution_time_barchart(experiment_results)

    plot_avg_noise_barchart(experiment_results)
    plot_delivered_orders_barchart(experiment_results)

    [analyze_and_plot_noise_increase(experiment_results, db) for db in range(55, 60, 5)]
    [analyze_and_plot_population_impact(experiment_results, db) for db in range(55, 60, 5)]


def run_drone_number_change_experiment(load_saved_results=False):
    run_complex_experiment(
        load_saved_results=load_saved_results,
        result_file_name="drone_number_change",
        experiment_function=drone_number_change_experiment,
        visualisation_function=plot_all_statistics
    )