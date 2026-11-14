"""Writers of the derived 100 m files of the revision design, for the data catalogue."""
from census_analysis.cell_datasets import load_cell_population
from common.enum import BaselineNoiseMap
from datasets.round4_baseline import write_round4_baseline_file

FINE_CELL_SIZE_M = 100


def write_fine_cell_population_file():
    load_cell_population(FINE_CELL_SIZE_M)


def write_fine_round4_baseline_file():
    write_round4_baseline_file(BaselineNoiseMap.ROUND_4_ROAD, FINE_CELL_SIZE_M)
