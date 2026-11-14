from experiments.config_generator import build_configs_for_single
from experiments.experiment_executor import run_complex_experiment
from census_analysis.cell_datasets import load_cell_age, load_cell_ethnicity
from visualiser.paper_experiment_figures import draw_single_run_figures


def plot_all_statistics(experiment_results, figure_directory):
    cell_table = experiment_results.iloc[0]['noise_impact_df']
    draw_single_run_figures(cell_table, figure_directory, load_cell_age(), load_cell_ethnicity())


def run_standard_experiment(load_saved_results=False):
    configs_with_names = build_configs_for_single("simple")

    run_complex_experiment(
        load_saved_results=load_saved_results,
        result_file_name="simple",
        configs_with_names=configs_with_names,
        visualisation_function=plot_all_statistics
    )
