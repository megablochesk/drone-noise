"""The catalogue of data files the model reads: complete, consistent, and able to generate what it claims."""
import pytest

from common.enum import BoundaryDatum
from common.path_configs import (
    BASE_NOISE_PATH,
    CELL_AGE_PATH,
    CELL_ETHNICITY_PATH,
    CELL_POPULATION_PATH,
    ORDER_BASE_PATH_CLOSEST,
    ORDER_BASE_PATH_FURTHEST,
    ORDER_BASE_PATH_RANDOM,
    PATH_CONFIGS,
    ROUND4_BASE_NOISE_PATH,
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
    PATH_CONFIGS.round4_road_noise_raster_path,
    ROUND4_BASE_NOISE_PATH,
    PATH_CONFIGS.round4_base_noise_path(100),
    PATH_CONFIGS.cell_population_path(100),
]
PATHS_OF_THE_FINE_GRID_DESIGN = [
    PATH_CONFIGS.cell_population_path(100, BoundaryDatum.OSGB36),
    PATH_CONFIGS.cell_age_path(100, BoundaryDatum.OSGB36),
    PATH_CONFIGS.cell_ethnicity_path(100, BoundaryDatum.OSGB36),
]


def test_names_and_paths_are_unique():
    assert len({data_file.name for data_file in DATA_CATALOGUE}) == len(DATA_CATALOGUE)
    assert len({data_file.relative_path for data_file in DATA_CATALOGUE}) == len(DATA_CATALOGUE)


@pytest.mark.parametrize(
    "path", PATHS_THE_STRAIGHT_LINE_MODEL_READS + PATHS_OF_OTHER_ANALYSES + PATHS_OF_THE_FINE_GRID_DESIGN
)
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


def find_data_file(name: str):
    return next(data_file for data_file in DATA_CATALOGUE if data_file.name == name)


@pytest.mark.parametrize("name", ["baseline noise", "navigation baseline noise"])
def test_baseline_noise_names_the_defra_source_of_the_paper(name):
    obtained_from = find_data_file(name).obtained_from
    assert "Defra" in obtained_from
    assert "https://www.gov.uk/government/publications/strategic-noise-mapping-2019" in obtained_from


@pytest.mark.parametrize("name", ["msoa population", "census age", "census ethnicity"])
def test_census_files_name_the_ons_census(name):
    assert "Office for National Statistics" in find_data_file(name).obtained_from
    assert "Census 2021" in find_data_file(name).obtained_from


def test_no_file_is_left_without_any_statement_of_origin():
    for data_file in DATA_CATALOGUE:
        assert "source not recorded in the repository" != data_file.obtained_from, data_file.name


def test_round_four_baseline_is_derived_from_the_downloaded_raster():
    raster, baseline = find_data_file("round 4 road noise raster"), find_data_file("baseline noise round 4")
    assert raster.origin is DataOrigin.EXTERNAL
    assert "datasets.download_round4_road_noise" in raster.obtained_from
    assert "https://environment.data.gov.uk/spatialdata/road-noise-all-metrics-england-round-4/wcs" in raster.obtained_from
    assert baseline.origin is DataOrigin.DERIVED
    assert baseline.requires == ("round 4 road noise raster",)
    assert baseline.generator == "datasets.round4_baseline:write_round4_baseline_file"


def test_fine_grid_files_are_derived_and_can_be_generated():
    """The 100 m files of the revision design: population from the MSOA data, baseline from the Round 4 raster."""
    population, baseline = find_data_file("cell population 100 m"), find_data_file("baseline noise round 4, 100 m")
    assert population.origin is baseline.origin is DataOrigin.DERIVED
    assert population.requires == ("study boundary", "msoa population")
    assert baseline.requires == ("round 4 road noise raster",)
    assert callable(resolve_generator(population.generator)) and callable(resolve_generator(baseline.generator))


@pytest.mark.parametrize("name, requirement", [
    ("cell age 100 m", "census age"), ("cell ethnicity 100 m", "census ethnicity"),
])
def test_fine_group_tables_are_derived_and_can_be_generated(name, requirement):
    """The 100 m age and ethnicity tables behind the demographic figures of the revision design."""
    group_table = find_data_file(name)
    assert group_table.origin is DataOrigin.DERIVED
    assert group_table.requires == ("study boundary", "msoa population", requirement)
    assert callable(resolve_generator(group_table.generator))


@pytest.mark.parametrize("name", ["baseline noise round 4 energy mean", "baseline noise round 4 energy mean, 100 m"])
def test_energy_mean_baselines_are_derived_and_can_be_generated(name):
    """The alternative cell average of the Round 4 raster, compared with the default in the fine-grid summary."""
    baseline = find_data_file(name)
    assert baseline.origin is DataOrigin.DERIVED
    assert baseline.requires == ("round 4 road noise raster",)
    assert callable(resolve_generator(baseline.generator))
