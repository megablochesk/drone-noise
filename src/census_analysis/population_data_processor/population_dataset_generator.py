from census_analysis.population_data_processor.cell_matrix_population_calculator import calculate_cell_matrix_population
from common.file_utils import path_exists, save_dataframe_to_pickle, load_dataframe_from_pickle
from common.path_configs import CELL_POPULATION_PATH
from visualiser.plot_utils import finalise_visualisation, plot_standalone_heatmap


def load_or_compute_ethnicity_dataset(pickle_path: str, try_from_file: bool = False):
    if try_from_file and path_exists(pickle_path):
        return load_dataframe_from_pickle(pickle_path)

    result = calculate_cell_matrix_population()

    save_dataframe_to_pickle(result, pickle_path)

    return result


def plot_heatmap_for_population_data(population_df):
    metric = "population"
    plot_standalone_heatmap(
        population_df,
        index="row",
        columns="col",
        values=metric,
        vmin=None,
        vmax=None,
        xlabel="Column",
        ylabel="Row",
        filename=metric,
    )


def compute_and_visualise_ethnicity_data():
    population_dataset_df = load_or_compute_ethnicity_dataset(CELL_POPULATION_PATH)

    plot_heatmap_for_population_data(population_dataset_df)

    finalise_visualisation()
