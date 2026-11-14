"""The catalogue of data files the model reads: complete, consistent, and able to generate what it claims."""
import pytest

from common.path_configs import (
    BASE_NOISE_PATH,
    CELL_AGE_PATH,
    CELL_ETHNICITY_PATH,
    CELL_POPULATION_PATH,
    ORDER_BASE_PATH_CLOSEST,
    ORDER_BASE_PATH_FURTHEST,
    ORDER_BASE_PATH_RANDOM,
    PATH_CONFIGS,
    get_experiment_results_full_file_path,
)
from datasets.data_catalogue import DATA_CATALOGUE, DataOrigin
from datasets.data_manifest import resolve_generator

PATHS_THE_STRAIGHT_LINE_MODEL_READS = [
    PATH_CONFIGS.london_boundaries_path,
    PATH_CONFIGS.msoa_population_path,
    BASE_NOISE_PATH,
    CELL_POPULATION_PATH,
    ORDER_BASE_PATH_CLOSEST,
    ORDER_BASE_PATH_RANDOM,
    ORDER_BASE_PATH_FURTHEST,
]
PATHS_OF_OTHER_ANALYSES = [
    CELL_AGE_PATH,
    CELL_ETHNICITY_PATH,
    PATH_CONFIGS.age_dataset_path,
    PATH_CONFIGS.ethnicity_dataset_path,
    get_experiment_results_full_file_path("drone_number_change"),
    get_experiment_results_full_file_path("drone_landing_on"),
]


def test_names_and_paths_are_unique():
    assert len({data_file.name for data_file in DATA_CATALOGUE}) == len(DATA_CATALOGUE)
    assert len({data_file.relative_path for data_file in DATA_CATALOGUE}) == len(DATA_CATALOGUE)


@pytest.mark.parametrize("path", PATHS_THE_STRAIGHT_LINE_MODEL_READS + PATHS_OF_OTHER_ANALYSES)
def test_file_the_code_reads_is_in_the_catalogue(path):
    assert path in {data_file.relative_path for data_file in DATA_CATALOGUE}


def test_exactly_the_derived_files_have_a_generator():
    for data_file in DATA_CATALOGUE:
        assert (data_file.generator is not None) == (data_file.origin is DataOrigin.DERIVED), data_file.name


def test_every_generator_exists():
    for data_file in DATA_CATALOGUE:
        if data_file.generator is not None:
            assert callable(resolve_generator(data_file.generator)), data_file.name


def test_requirements_name_catalogued_files():
    names = {data_file.name for data_file in DATA_CATALOGUE}
    for data_file in DATA_CATALOGUE:
        assert set(data_file.requires) <= names, data_file.name


def test_every_file_says_what_it_is_and_where_it_comes_from():
    for data_file in DATA_CATALOGUE:
        assert data_file.description and data_file.obtained_from, data_file.name
