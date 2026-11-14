"""Per-cell census datasets: read on first use, computed and saved first if the file does not exist yet."""
from functools import lru_cache
from typing import Callable

import pandas as pd

from census_analysis.age_data_processor.age_cell_matrix_calculator import calculate_cell_matrix_age
from census_analysis.ethnicity_data_processor.ethnicity_cell_matrix_calculator import calculate_cell_matrix_ethnicity
from census_analysis.population_data_processor.cell_matrix_population_calculator import calculate_cell_matrix_population
from common.file_utils import load_dataframe_from_pickle, path_exists, save_dataframe_to_pickle
from common.path_configs import CELL_AGE_PATH, CELL_ETHNICITY_PATH, CELL_POPULATION_PATH


def load_or_compute_dataset(pickle_path: str, compute_dataset: Callable[[], pd.DataFrame]) -> pd.DataFrame:
    if path_exists(pickle_path):
        return load_dataframe_from_pickle(pickle_path)

    dataset = compute_dataset()
    save_dataframe_to_pickle(dataset, pickle_path)
    return dataset


@lru_cache(maxsize=1)
def load_cell_population() -> pd.DataFrame:
    return load_or_compute_dataset(CELL_POPULATION_PATH, calculate_cell_matrix_population)


@lru_cache(maxsize=1)
def load_cell_age() -> pd.DataFrame:
    return load_or_compute_dataset(CELL_AGE_PATH, calculate_cell_matrix_age)


@lru_cache(maxsize=1)
def load_cell_ethnicity() -> pd.DataFrame:
    return load_or_compute_dataset(CELL_ETHNICITY_PATH, calculate_cell_matrix_ethnicity)
