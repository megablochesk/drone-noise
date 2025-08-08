from common.configuration import TOTAL_ORDER_NUMBER, TOTAL_DRONE_NUMBER, ORDER_BASE_PATH
from experiments.simulation_based_experiment_utils import run_atomic_experiment, run_complex_experiment
from visualiser.plot_noise_level_comparison import plot_noise_level_comparison
from visualiser.plot_utils import finalise_visualisation
from visualiser.statistics import plot_noise_difference_barchart


def simple_experiment():
    return run_atomic_experiment(
        'simple',
        ORDER_BASE_PATH,
        TOTAL_ORDER_NUMBER,
        TOTAL_DRONE_NUMBER
    )


def plot_all_statistics(experiment_results):
    noise_impact_df = experiment_results.iloc[0]['noise_impact_df']

    plot_noise_difference_barchart(noise_impact_df)

    plot_noise_level_comparison(
        noise_impact_df,
        vmin=[40, 25, 0],
        vmax=[80, 35, 1]
    )

    finalise_visualisation()


def run_standard_experiment(load_saved_results=False):
    run_complex_experiment(
        load_saved_results=load_saved_results,
        result_file_name="simple",
        experiment_function=simple_experiment,
        visualisation_function=plot_all_statistics
    )
