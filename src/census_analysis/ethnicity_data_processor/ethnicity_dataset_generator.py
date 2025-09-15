import pandas as pd

from census_analysis.census_data_heatmap_plotter import plot_heatmaps_for_census_data
from census_analysis.ethnicity_data_processor.ethnicity_cell_matrix_calculator import calculate_cell_matrix_ethnicity
from common.file_utils import path_exists, save_dataframe_to_pickle
from common.path_configs import CELL_ETHNICITY_PATH
from visualiser.plot_utils import finalise_visualisation


def load_or_compute_ethnicity_dataset(pickle_path: str, try_from_file: bool = False) -> pd.DataFrame:
    if try_from_file and path_exists(pickle_path):
        return pd.read_pickle(pickle_path)

    result = calculate_cell_matrix_ethnicity()

    save_dataframe_to_pickle(result, pickle_path)

    return result


def compute_and_visualise_ethnicity_data():
    ethnicity_dataset_df = load_or_compute_ethnicity_dataset(CELL_ETHNICITY_PATH)

    plot_heatmaps_for_census_data(
        ethnicity_dataset_df,
        data_category="ethnicity",
        vmin=0.0, vmax=1000.0
    )

    finalise_visualisation()
