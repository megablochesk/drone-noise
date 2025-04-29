from common.configuration import TOTAL_ORDER_NUMBER, TOTAL_DRONE_NUMBER, ORDER_BASE_PATH
from experiments.simulation_based_experiment_utils import run_atomic_experiment
from visualiser.plot_noise_level_comparison import plot_noise_level_comparison
from visualiser.plot_utils import plot_figures
from visualiser.statistics import plot_noise_change_barchart


def simple_experiment():
    return run_atomic_experiment(
        'simple',
        ORDER_BASE_PATH,
        TOTAL_ORDER_NUMBER,
        TOTAL_DRONE_NUMBER
    )


def plot_all_statistics(experiment_results):
    noise_impact_df = experiment_results['noise_impact_df']

    plot_noise_change_barchart(noise_impact_df)

    plot_noise_level_comparison(noise_impact_df)

    plot_figures()


def run_standard_experiment():
    results = simple_experiment()

    plot_all_statistics(results)
