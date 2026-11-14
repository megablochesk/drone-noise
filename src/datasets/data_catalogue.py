"""Every data file the model reads: what it is, where it comes from, and what can write it when it is missing.

None of these files is under version control. Paths are relative to src/, like all data paths of the model.
"""
from dataclasses import dataclass
from enum import Enum

from common.path_configs import (
    BASE_NOISE_PATH,
    CELL_AGE_PATH,
    CELL_ETHNICITY_PATH,
    CELL_POPULATION_PATH,
    NAVIGATION_BASE_NOISE_PATH,
    NAVIGATION_GRAPH_PATH,
    ORDER_BASE_PATH_CLOSEST,
    ORDER_BASE_PATH_FURTHEST,
    ORDER_BASE_PATH_RANDOM,
    PATH_CONFIGS,
    get_experiment_results_full_file_path,
    get_mixed_order_dataset_pattern,
)

PUBLISHED_NUMBER_OF_ORDERS = 100_000
MIXED_STOCKING_RANDOM_SHARES_PERCENT = tuple(range(100, 0, -10))
SOURCE_NOT_RECORDED = "source not recorded in the repository"
SINGLE_STOCKING_GENERATOR = "orders.order_generator.generate_datasets(100_000), unseeded: a rerun gives other orders"
MIXED_STOCKING_GENERATOR = (
    "orders.order_generator.generate_mixed_stocking_datasets(100_000), unseeded: a rerun gives other orders"
)
PUBLISHED_EXPERIMENT = "experiments.experiment_executor, the published straight-line experiments (hours of run time)"


class DataOrigin(Enum):
    EXTERNAL = "external"    # obtained outside this repository
    PUBLISHED = "published"  # written once for the paper; regenerating it gives different data
    DERIVED = "derived"      # computed from other files; generated automatically when missing
    CACHE = "cache"          # built on first use by the code that needs it


@dataclass(frozen=True)
class DataFile:
    name: str
    relative_path: str
    origin: DataOrigin
    description: str
    obtained_from: str
    generator: str | None = None
    requires: tuple[str, ...] = ()


EXTERNAL_FILES = (
    DataFile(
        "study boundary", PATH_CONFIGS.london_boundaries_path, DataOrigin.EXTERNAL,
        "Greater London boundary polygons; cells and depots outside it are dropped", SOURCE_NOT_RECORDED,
    ),
    DataFile(
        "msoa population", PATH_CONFIGS.msoa_population_path, DataOrigin.EXTERNAL,
        "MSOA 2021 polygons in British National Grid with a 'population' property; weights of the order destinations",
        SOURCE_NOT_RECORDED,
    ),
    DataFile(
        "baseline noise", BASE_NOISE_PATH, DataOrigin.EXTERNAL,
        "baseline environmental noise level of every 500 m cell (row, col, noise_level)", SOURCE_NOT_RECORDED,
    ),
    DataFile(
        "navigation baseline noise", NAVIGATION_BASE_NOISE_PATH, DataOrigin.EXTERNAL,
        "baseline noise on the 100 m navigation grid; noise-based navigation only", SOURCE_NOT_RECORDED,
    ),
    DataFile(
        "census age", PATH_CONFIGS.age_dataset_path, DataOrigin.EXTERNAL,
        "Census 2021 residents by single year of age and MSOA", SOURCE_NOT_RECORDED,
    ),
    DataFile(
        "census ethnicity", PATH_CONFIGS.ethnicity_dataset_path, DataOrigin.EXTERNAL,
        "Census 2021 residents by ethnic group and MSOA", SOURCE_NOT_RECORDED,
    ),
)

PUBLISHED_FILES = (
    DataFile(
        "orders closest", ORDER_BASE_PATH_CLOSEST, DataOrigin.PUBLISHED,
        "100,000 published orders, each stocked at the closest warehouse", SINGLE_STOCKING_GENERATOR,
    ),
    DataFile(
        "orders random", ORDER_BASE_PATH_RANDOM, DataOrigin.PUBLISHED,
        "100,000 published orders, each stocked at a random warehouse", SINGLE_STOCKING_GENERATOR,
    ),
    DataFile(
        "orders furthest", ORDER_BASE_PATH_FURTHEST, DataOrigin.PUBLISHED,
        "100,000 published orders, each stocked at the furthest warehouse", SINGLE_STOCKING_GENERATOR,
    ),
    *(
        DataFile(
            f"orders mixed random {random_share}", get_mixed_order_dataset_pattern(
                random_share, 100 - random_share, PUBLISHED_NUMBER_OF_ORDERS
            ),
            DataOrigin.PUBLISHED,
            f"100,000 published orders, {random_share} % random and {100 - random_share} % closest stocking",
            MIXED_STOCKING_GENERATOR,
        )
        for random_share in MIXED_STOCKING_RANDOM_SHARES_PERCENT
    ),
    DataFile(
        "published results cruise only", get_experiment_results_full_file_path("drone_number_change"), DataOrigin.PUBLISHED,
        "published result maps without terminal phases; reference of the regression tests", PUBLISHED_EXPERIMENT,
    ),
    DataFile(
        "published results terminal phases", get_experiment_results_full_file_path("drone_landing_on"), DataOrigin.PUBLISHED,
        "published result maps with terminal phases; reference of the regression tests", PUBLISHED_EXPERIMENT,
    ),
)

DERIVED_FILES = (
    DataFile(
        "cell population", CELL_POPULATION_PATH, DataOrigin.DERIVED,
        "residents of every 500 m cell, MSOA populations split by overlapping area",
        "census_analysis.cell_datasets.load_cell_population",
        generator="census_analysis.cell_datasets:load_cell_population", requires=("study boundary", "msoa population"),
    ),
    DataFile(
        "cell age", CELL_AGE_PATH, DataOrigin.DERIVED,
        "residents of every 500 m cell by age band", "census_analysis.cell_datasets.load_cell_age",
        generator="census_analysis.cell_datasets:load_cell_age",
        requires=("study boundary", "msoa population", "census age"),
    ),
    DataFile(
        "cell ethnicity", CELL_ETHNICITY_PATH, DataOrigin.DERIVED,
        "residents of every 500 m cell by ethnic group", "census_analysis.cell_datasets.load_cell_ethnicity",
        generator="census_analysis.cell_datasets:load_cell_ethnicity",
        requires=("study boundary", "msoa population", "census ethnicity"),
    ),
)

CACHE_FILES = (
    DataFile(
        "navigation graph", f"{NAVIGATION_GRAPH_PATH}.pkl", DataOrigin.CACHE,
        "routing graph of the noise-based navigation; its route caches next to it are built the same way",
        "noise.noise_graph_builder.load_or_build_graph, on first use", requires=("navigation baseline noise",),
    ),
)

DATA_CATALOGUE = (*EXTERNAL_FILES, *PUBLISHED_FILES, *DERIVED_FILES, *CACHE_FILES)
