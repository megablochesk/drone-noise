"""Every data file the model and the revision design read: what it is, where it comes from, and what can write
it when it is missing.

None of these files is under version control. Paths are relative to src/, like all data paths of the model.
"""
from dataclasses import dataclass
from enum import Enum

from common.enum import BoundaryDatum
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
    ROUND4_BASE_NOISE_PATH,
    get_experiment_results_full_file_path,
    get_mixed_order_dataset_pattern,
)

PUBLISHED_NUMBER_OF_ORDERS = 100_000
FINE_CELL_SIZE_M = 100
PUBLISHED_CELL_SIZE_M = 500
FINE_GRID_BOUNDARY_DATUM = BoundaryDatum.OSGB36
PUBLISHED_READING = "boundary read as WGS84, as the published model reads it"
OSGB36_READING = "boundary read on OSGB36, the datum of the boundary file; the cells of the fine-grid designs"
MIXED_STOCKING_RANDOM_SHARES_PERCENT = tuple(range(100, 0, -10))
DEFRA_NOISE_MAPS = (
    "Defra strategic noise mapping, 2017 noise maps (https://www.gov.uk/government/publications/strategic-noise-mapping-2019): "
    "10 m cells in bands from 55 dB, 40 dB where unmapped, aggregated to grid cells; the aggregation script is not in this repository"
)
ONS_CENSUS = "Office for National Statistics, Census 2021"
ONS_POPULATION = (
    f"{ONS_CENSUS} population (the paper cites the output area population estimates, mid-2021) on MSOA 2021 polygons "
    "downloaded from a public source; the exact polygon source and the conversion are not recorded"
)
DEFRA_ROUND4_ROAD_NOISE = (
    "Defra Road Noise - All Metrics - England Round 4, LAeq,16h, all roads, 10 m pixels "
    "(https://environment.data.gov.uk/spatialdata/road-noise-all-metrics-england-round-4/wcs); "
    "downloaded by python -m datasets.download_round4_road_noise"
)
PUBLIC_DOWNLOAD = "downloaded from a public source on the internet; the exact source is not recorded"
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
        "Greater London boundary polygons; cells and depots outside it are dropped", PUBLIC_DOWNLOAD,
    ),
    DataFile(
        "msoa population", PATH_CONFIGS.msoa_population_path, DataOrigin.EXTERNAL,
        "MSOA 2021 polygons in British National Grid with a 'population' property; weights of the order destinations",
        ONS_POPULATION,
    ),
    DataFile(
        "baseline noise", BASE_NOISE_PATH, DataOrigin.EXTERNAL,
        "baseline environmental noise level of every 500 m cell (row, col, noise_level)", DEFRA_NOISE_MAPS,
    ),
    DataFile(
        "navigation baseline noise", NAVIGATION_BASE_NOISE_PATH, DataOrigin.EXTERNAL,
        "baseline noise on the 100 m navigation grid; noise-based navigation on the published map only", DEFRA_NOISE_MAPS,
    ),
    DataFile(
        "round 4 road noise raster", PATH_CONFIGS.round4_road_noise_raster_path, DataOrigin.EXTERNAL,
        "road noise level LAeq,16h of every 10 m pixel of the study box; 0 below 40 dB, -96 where not modelled",
        DEFRA_ROUND4_ROAD_NOISE,
    ),
    DataFile(
        "census age", PATH_CONFIGS.age_dataset_path, DataOrigin.EXTERNAL,
        "residents by single year of age and MSOA", f"{ONS_CENSUS}, table of age by MSOA",
    ),
    DataFile(
        "census ethnicity", PATH_CONFIGS.ethnicity_dataset_path, DataOrigin.EXTERNAL,
        "residents by ethnic group and MSOA", f"{ONS_CENSUS}, table of ethnic group by MSOA",
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
        "cell population 100 m", PATH_CONFIGS.cell_population_path(FINE_CELL_SIZE_M), DataOrigin.DERIVED,
        f"residents of every 100 m cell, MSOA populations split by overlapping area; {PUBLISHED_READING}",
        "census_analysis.cell_datasets.load_cell_population(100)",
        generator="datasets.fine_grid_files:write_fine_cell_population_file", requires=("study boundary", "msoa population"),
    ),
    DataFile(
        "baseline noise round 4, 100 m", PATH_CONFIGS.round4_base_noise_path(FINE_CELL_SIZE_M), DataOrigin.DERIVED,
        "Round 4 road noise averaged over every 100 m cell, 40 dB where the map reports nothing",
        "datasets.round4_baseline.write_round4_baseline_file(ROUND_4_ROAD, 100)",
        generator="datasets.fine_grid_files:write_fine_round4_baseline_file", requires=("round 4 road noise raster",),
    ),
    DataFile(
        "cell age 100 m", PATH_CONFIGS.cell_age_path(FINE_CELL_SIZE_M), DataOrigin.DERIVED,
        f"residents of every 100 m cell by age band; {PUBLISHED_READING}",
        "census_analysis.cell_datasets.load_cell_age(100)",
        generator="datasets.fine_grid_files:write_fine_cell_age_file",
        requires=("study boundary", "msoa population", "census age"),
    ),
    DataFile(
        "cell ethnicity 100 m", PATH_CONFIGS.cell_ethnicity_path(FINE_CELL_SIZE_M), DataOrigin.DERIVED,
        f"residents of every 100 m cell by ethnic group; {PUBLISHED_READING}",
        "census_analysis.cell_datasets.load_cell_ethnicity(100)",
        generator="datasets.fine_grid_files:write_fine_cell_ethnicity_file",
        requires=("study boundary", "msoa population", "census ethnicity"),
    ),
    DataFile(
        "cell population 100 m osgb36", PATH_CONFIGS.cell_population_path(FINE_CELL_SIZE_M, FINE_GRID_BOUNDARY_DATUM),
        DataOrigin.DERIVED,
        f"residents of every 100 m cell, MSOA populations split by overlapping area; {OSGB36_READING}",
        "census_analysis.cell_datasets.load_cell_population(100, BoundaryDatum.OSGB36)",
        generator="datasets.fine_grid_files:write_osgb36_fine_cell_population_file",
        requires=("study boundary", "msoa population"),
    ),
    DataFile(
        "cell age 100 m osgb36", PATH_CONFIGS.cell_age_path(FINE_CELL_SIZE_M, FINE_GRID_BOUNDARY_DATUM),
        DataOrigin.DERIVED, f"residents of every 100 m cell by age band; {OSGB36_READING}",
        "census_analysis.cell_datasets.load_cell_age(100, BoundaryDatum.OSGB36)",
        generator="datasets.fine_grid_files:write_osgb36_fine_cell_age_file",
        requires=("study boundary", "msoa population", "census age"),
    ),
    DataFile(
        "cell ethnicity 100 m osgb36", PATH_CONFIGS.cell_ethnicity_path(FINE_CELL_SIZE_M, FINE_GRID_BOUNDARY_DATUM),
        DataOrigin.DERIVED, f"residents of every 100 m cell by ethnic group; {OSGB36_READING}",
        "census_analysis.cell_datasets.load_cell_ethnicity(100, BoundaryDatum.OSGB36)",
        generator="datasets.fine_grid_files:write_osgb36_fine_cell_ethnicity_file",
        requires=("study boundary", "msoa population", "census ethnicity"),
    ),
    DataFile(
        "baseline noise round 4 energy mean, 100 m", PATH_CONFIGS.round4_energy_base_noise_path(FINE_CELL_SIZE_M),
        DataOrigin.DERIVED, "Round 4 road noise as the level of the mean sound energy of every 100 m cell",
        "datasets.round4_baseline.write_round4_baseline_file(ROUND_4_ROAD_ENERGY, 100)",
        generator="datasets.fine_grid_files:write_fine_round4_energy_baseline_file", requires=("round 4 road noise raster",),
    ),
    DataFile(
        "baseline noise round 4 energy mean", PATH_CONFIGS.round4_energy_base_noise_path(PUBLISHED_CELL_SIZE_M),
        DataOrigin.DERIVED, "Round 4 road noise as the level of the mean sound energy of every 500 m cell",
        "datasets.round4_baseline.write_round4_baseline_file(ROUND_4_ROAD_ENERGY, 500)",
        generator="datasets.fine_grid_files:write_round4_energy_baseline_file", requires=("round 4 road noise raster",),
    ),
    DataFile(
        "baseline noise round 4", ROUND4_BASE_NOISE_PATH, DataOrigin.DERIVED,
        "Round 4 road noise averaged over every 500 m cell, 40 dB where the map reports nothing",
        "datasets.round4_baseline.write_round4_baseline_file",
        generator="datasets.round4_baseline:write_round4_baseline_file", requires=("round 4 road noise raster",),
    ),
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
        "routing graph of noise-based navigation on the published map; its route caches are built the same way",
        "noise.noise_graph_builder.load_or_build_graph, on first use", requires=("navigation baseline noise",),
    ),
)

DATA_CATALOGUE = (*EXTERNAL_FILES, *PUBLISHED_FILES, *DERIVED_FILES, *CACHE_FILES)
