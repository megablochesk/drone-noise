"""Residents of grid cells by group (age band, ethnic group): each region's count of a group is split over the
cells by the share of the region's area in each cell, as the population is."""
import numpy as np
import pytest
from shapely.geometry import box

from census_analysis.cell_datasets import load_cell_age, load_cell_ethnicity, load_cell_population
from census_analysis.population_data_processor.cell_matrix_population_calculator import (
    split_group_counts_by_overlapping_area,
)

WEST_REGION, EAST_REGION = box(0.0, 0.0, 20.0, 10.0), box(20.0, 0.0, 40.0, 10.0)
# Rows are regions, columns are groups.
REGION_GROUP_COUNTS = np.array([[100.0, 8.0], [60.0, 0.0]])
FINE_CELL_SIZE_M = 100
FINE_CELLS_PER_PUBLISHED_CELL_SIDE = 5


def test_each_group_is_split_by_the_share_of_the_region_in_the_cell():
    """Cell from 15 to 25 m holds a quarter of each region: (25 + 15, 2 + 0). Cell 0-10 m: half of the west."""
    cells = [box(15.0, 0.0, 25.0, 10.0), box(0.0, 0.0, 10.0, 10.0), box(50.0, 0.0, 60.0, 10.0)]

    counts = split_group_counts_by_overlapping_area(cells, [WEST_REGION, EAST_REGION], REGION_GROUP_COUNTS)

    np.testing.assert_allclose(counts, [[40.0, 2.0], [50.0, 4.0], [0.0, 0.0]], rtol=1e-12)


def sum_fine_cells_by_published_cell(fine, group_codes):
    return fine.assign(
        row=fine["row"] // FINE_CELLS_PER_PUBLISHED_CELL_SIDE, col=fine["col"] // FINE_CELLS_PER_PUBLISHED_CELL_SIDE
    ).groupby(["row", "col"])[group_codes].sum().rename(columns=lambda code: f"{code}_fine").reset_index()


@pytest.mark.parametrize("load_dataset", [load_cell_age, load_cell_ethnicity], ids=["age", "ethnicity"])
def test_fine_cells_add_up_to_their_published_cell_for_every_group(load_dataset):
    """As for the population: where all 25 fine cells of a 500 m cell are grid cells, their sum is its value."""
    fine, published = load_dataset(FINE_CELL_SIZE_M), load_dataset()
    group_codes = [column for column in published.columns if isinstance(column, (int, np.integer))]
    number_of_fine_cells = fine.assign(
        row=fine["row"] // FINE_CELLS_PER_PUBLISHED_CELL_SIDE, col=fine["col"] // FINE_CELLS_PER_PUBLISHED_CELL_SIDE
    ).groupby(["row", "col"]).size().rename("number_of_fine_cells").reset_index()
    merged = published.merge(
        sum_fine_cells_by_published_cell(fine, group_codes), on=["row", "col"], validate="1:1"
    ).merge(number_of_fine_cells, on=["row", "col"], validate="1:1")
    complete = merged[merged["number_of_fine_cells"] == FINE_CELLS_PER_PUBLISHED_CELL_SIDE ** 2]

    assert fine.attrs == published.attrs
    assert len(fine) == len(load_cell_population(FINE_CELL_SIZE_M)) and len(complete) > 0.8 * len(published)
    for code in group_codes:
        np.testing.assert_allclose(complete[f"{code}_fine"], complete[code], rtol=1e-9, atol=1e-6)
        assert (merged[f"{code}_fine"] <= merged[code] + 1e-6).all()
