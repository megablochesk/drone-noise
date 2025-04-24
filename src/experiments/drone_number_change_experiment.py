from common.configuration import (
    ORDER_BASE_PATH_FURTHEST, ORDER_BASE_PATH_RANDOM, ORDER_BASE_PATH_CLOSEST
)
from common.file_utils import save_dataframe_to_pickle
from experiments.simulation_based_experiment_utils import (
    convert_results_to_dataframe,
    process_datasets_and_drone_number_combinations,
    run_complex_experiment
)

from visualiser.plotter import (
    plot_avg_noise_barchart, plot_delivered_orders_barchart,
    analyze_and_plot_noise_increase,
    analyze_and_plot_population_impact, plot_cells_impacted_by_noise,
    plot_execution_time_barchart
)

ORDER_DATASETS = {
    'furthest': ORDER_BASE_PATH_FURTHEST,
    'random': ORDER_BASE_PATH_RANDOM,
    'closest': ORDER_BASE_PATH_CLOSEST
}

NUMBER_OF_DRONES_CASES = [100, 250, 500, 750, 1000, 1250]
NUMBER_OF_ORDERS = 100000


def unlimited_orders_limited_time_experiment(results_path):
    datasets = ORDER_DATASETS.items()
    results = process_datasets_and_drone_number_combinations(datasets, NUMBER_OF_ORDERS, NUMBER_OF_DRONES_CASES)

    results_df = convert_results_to_dataframe(results)

    save_dataframe_to_pickle(results_df, results_path)

    return results_df


def plot_all_statistics(experiment_results):
    plot_cells_impacted_by_noise(experiment_results, 55)

    plot_execution_time_barchart(experiment_results)

    plot_avg_noise_barchart(experiment_results)
    plot_delivered_orders_barchart(experiment_results)

    [analyze_and_plot_noise_increase(experiment_results, db) for db in range(55, 60, 5)]
    [analyze_and_plot_population_impact(experiment_results, db) for db in range(55, 60, 5)]


def run_drone_number_change_experiment():
    results_file = "noise_maps_df_1.pkl"
    from_file = True

    run_complex_experiment(
        results_file,
        from_file,
        unlimited_orders_limited_time_experiment,
        plot_all_statistics
    )