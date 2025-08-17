from experiments.config_generator import build_configs_for_single
from experiments.experiment_executor import run_complex_experiment
from visualiser.plot_noise_level_comparison import plot_noise_level_comparison
from visualiser.plot_utils import finalise_visualisation
from visualiser.statistics import plot_noise_difference_barchart


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
    configs_with_names = build_configs_for_single("simple")

    run_complex_experiment(
        load_saved_results=load_saved_results,
        result_file_name="simple",
        configs_with_names=configs_with_names,
        visualisation_function=plot_all_statistics
    )
