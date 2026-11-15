"""Writers of the derived files of the revision design (100 m tables, energy-mean baselines), for the catalogue."""
from census_analysis.cell_datasets import load_cell_age, load_cell_ethnicity, load_cell_population
from common.enum import BaselineNoiseMap, BoundaryDatum
from datasets.round4_baseline import write_round4_baseline_file
from noise.noise_data_processor import PUBLISHED_CELL_SIZE_M

FINE_CELL_SIZE_M = 100
FINE_GRID_BOUNDARY_DATUM = BoundaryDatum.OSGB36


def write_fine_cell_population_file():
    load_cell_population(FINE_CELL_SIZE_M)


def write_fine_round4_baseline_file():
    write_round4_baseline_file(BaselineNoiseMap.ROUND_4_ROAD, FINE_CELL_SIZE_M)


def write_fine_cell_age_file():
    load_cell_age(FINE_CELL_SIZE_M)


def write_fine_cell_ethnicity_file():
    load_cell_ethnicity(FINE_CELL_SIZE_M)


def write_osgb36_fine_cell_population_file():
    load_cell_population(FINE_CELL_SIZE_M, FINE_GRID_BOUNDARY_DATUM)


def write_osgb36_fine_cell_age_file():
    load_cell_age(FINE_CELL_SIZE_M, FINE_GRID_BOUNDARY_DATUM)


def write_osgb36_fine_cell_ethnicity_file():
    load_cell_ethnicity(FINE_CELL_SIZE_M, FINE_GRID_BOUNDARY_DATUM)


def write_round4_energy_baseline_file():
    write_round4_baseline_file(BaselineNoiseMap.ROUND_4_ROAD_ENERGY, PUBLISHED_CELL_SIZE_M)


def write_fine_round4_energy_baseline_file():
    write_round4_baseline_file(BaselineNoiseMap.ROUND_4_ROAD_ENERGY, FINE_CELL_SIZE_M)
