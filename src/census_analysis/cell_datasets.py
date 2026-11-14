"""Per-cell census datasets: read on first use, computed and saved first if the file does not exist yet."""
from functools import lru_cache
from typing import Callable

import pandas as pd

from census_analysis.age_data_processor.age_cell_matrix_calculator import calculate_cell_matrix_age
from census_analysis.ethnicity_data_processor.ethnicity_cell_matrix_calculator import calculate_cell_matrix_ethnicity
from census_analysis.population_data_processor.cell_matrix_population_calculator import calculate_cell_matrix_population
from common.file_utils import load_dataframe_from_pickle, path_exists, save_dataframe_to_pickle
from common.path_configs import PATH_CONFIGS
from noise.grid_generator import CELL_SIZE


def load_or_compute_dataset(pickle_path: str, compute_dataset: Callable[[], pd.DataFrame]) -> pd.DataFrame:
    if path_exists(pickle_path):
        return load_dataframe_from_pickle(pickle_path)

    dataset = compute_dataset()
    save_dataframe_to_pickle(dataset, pickle_path)
    return dataset


@lru_cache(maxsize=None)
def load_cell_population_once(cell_size_m: int) -> pd.DataFrame:
    return load_or_compute_dataset(
        PATH_CONFIGS.cell_population_path(cell_size_m), lambda: calculate_cell_matrix_population(cell_size_m)
    )


def load_cell_population(cell_size_m: int = CELL_SIZE) -> pd.DataFrame:
    return load_cell_population_once(cell_size_m)


@lru_cache(maxsize=None)
def load_cell_age_once(cell_size_m: int) -> pd.DataFrame:
    return load_or_compute_dataset(PATH_CONFIGS.cell_age_path(cell_size_m), lambda: calculate_cell_matrix_age(cell_size_m))


def load_cell_age(cell_size_m: int = CELL_SIZE) -> pd.DataFrame:
    return load_cell_age_once(cell_size_m)


@lru_cache(maxsize=None)
def load_cell_ethnicity_once(cell_size_m: int) -> pd.DataFrame:
    return load_or_compute_dataset(
        PATH_CONFIGS.cell_ethnicity_path(cell_size_m), lambda: calculate_cell_matrix_ethnicity(cell_size_m)
    )


def load_cell_ethnicity(cell_size_m: int = CELL_SIZE) -> pd.DataFrame:
    return load_cell_ethnicity_once(cell_size_m)
