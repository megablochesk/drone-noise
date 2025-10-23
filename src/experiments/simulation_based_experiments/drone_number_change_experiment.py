from common.path_configs import ORDER_BASE_PATH_FURTHEST, ORDER_BASE_PATH_RANDOM, ORDER_BASE_PATH_CLOSEST
from experiments.config_generator import build_configs_for_datasets_and_drones
from experiments.experiment_executor import run_complex_experiment
from visualiser.cell_statistics_plotter import analyze_and_plot_noise_increase, analyze_and_plot_population_impact, \
    analyze_and_plot_ethnicity_impact, analyze_and_plot_age_impact
from visualiser.general_statistics_plotter import plot_avg_noise_barchart, plot_delivered_orders_barchart, plot_execution_time_barchart

NUMBER_OF_DRONES_CASES = [100, 250, 500, 750, 1000, 1250]
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


def plot_all_statistics(experiment_results):
    plot_execution_time_barchart(experiment_results)

    plot_avg_noise_barchart(experiment_results)
    plot_delivered_orders_barchart(experiment_results)

    for dB_level in range(55, 60, 5):
        analyze_and_plot_noise_increase(experiment_results, dB_level)
        analyze_and_plot_population_impact(experiment_results, dB_level)
        analyze_and_plot_age_impact(experiment_results, dB_level)
        analyze_and_plot_ethnicity_impact(experiment_results, dB_level)


def run_drone_number_change_experiment(load_saved_results=False):
    run_complex_experiment(
        load_saved_results=load_saved_results,
        result_file_name="drone_number_change",
        configs_with_names=generate_configs(),
        visualisation_function=plot_all_statistics
    )
