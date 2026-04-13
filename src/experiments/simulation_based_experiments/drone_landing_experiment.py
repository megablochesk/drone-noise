from common.path_configs import ORDER_BASE_PATH_FURTHEST, ORDER_BASE_PATH_RANDOM, ORDER_BASE_PATH_CLOSEST
from experiments.config_generator import build_configs_for_datasets_and_drones
from experiments.experiment_executor import run_complex_experiment
from visualiser.cell_statistics_plotter import analyze_and_plot_noise_increase, analyze_and_plot_population_impact
from visualiser.general_statistics_plotter import plot_avg_noise_linegraph, plot_delivered_orders_linegraph

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
        NUMBER_OF_DRONES_CASES,
        drone_landing=True
    )


def plot_all_statistics(experiment_results):
    plot_avg_noise_linegraph(experiment_results, filename="del_noise_landing")
    plot_delivered_orders_linegraph(experiment_results, filename="del_orders_landing")

    for dB_level in range(55, 60, 5):
        analyze_and_plot_noise_increase(experiment_results, dB_level, filename="del_cel_imp_landing")
        analyze_and_plot_population_impact(experiment_results, dB_level, filename="del_pop_imp_landing")
        #analyze_and_plot_age_impact(experiment_results, dB_level)
        #analyze_and_plot_ethnicity_impact(experiment_results, dB_level)


def run_drone_landing_experiment(load_saved_results=False):
    run_complex_experiment(
        load_saved_results=load_saved_results,
        result_file_name="drone_landing_on",
        configs_with_names=generate_configs(),
        visualisation_function=plot_all_statistics
    )