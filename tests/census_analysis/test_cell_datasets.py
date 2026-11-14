"""Datasets are read on first use and kept; a derived dataset that is missing is computed and saved."""
import pandas as pd

from census_analysis.cell_datasets import (
    load_cell_age,
    load_cell_ethnicity,
    load_cell_population,
    load_or_compute_dataset,
)
from census_analysis.msoa_data import MSOAData, load_msoa_data
from common.file_utils import load_dataframe_from_pickle
from common.path_configs import CELL_AGE_PATH, CELL_ETHNICITY_PATH, CELL_POPULATION_PATH
from noise.noise_data_processor import load_base_noise_data, read_base_noise_data

GREATER_LONDON_MSOAS = 1_002
HAND_BUILT_DATASET = pd.DataFrame({"row": [0, 0, 1], "col": [0, 1, 0], "population": [10.0, 20.5, 0.0]})


def test_missing_dataset_is_computed_and_saved(tmp_path):
    dataset_path = tmp_path / "cell_population.pkl"
    computations = []

    def compute():
        computations.append("computed")
        return HAND_BUILT_DATASET

    loaded = load_or_compute_dataset(str(dataset_path), compute)

    pd.testing.assert_frame_equal(loaded, HAND_BUILT_DATASET)
    pd.testing.assert_frame_equal(load_dataframe_from_pickle(dataset_path), HAND_BUILT_DATASET)
    assert computations == ["computed"]


def test_existing_dataset_is_loaded_without_computing(tmp_path):
    dataset_path = tmp_path / "cell_population.pkl"
    HAND_BUILT_DATASET.to_pickle(dataset_path)

    def refuse_to_compute():
        raise AssertionError("the dataset exists and must not be computed again")

    pd.testing.assert_frame_equal(load_or_compute_dataset(str(dataset_path), refuse_to_compute), HAND_BUILT_DATASET)


def test_cell_datasets_are_the_stored_files_and_are_read_once():
    for load_dataset, dataset_path in [
        (load_cell_population, CELL_POPULATION_PATH), (load_cell_age, CELL_AGE_PATH), (load_cell_ethnicity, CELL_ETHNICITY_PATH),
    ]:
        pd.testing.assert_frame_equal(load_dataset(), load_dataframe_from_pickle(dataset_path))
        assert load_dataset() is load_dataset()


def test_base_noise_data_is_the_stored_map_and_is_read_once():
    pd.testing.assert_frame_equal(load_base_noise_data(), read_base_noise_data())
    assert load_base_noise_data() is load_base_noise_data()


def test_msoa_data_is_read_once():
    msoa_data = load_msoa_data()
    assert isinstance(msoa_data, MSOAData)
    assert load_msoa_data() is msoa_data
    assert len(msoa_data.msoa_populations) == len(msoa_data.msoa_index) == GREATER_LONDON_MSOAS
