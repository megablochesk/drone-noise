"""Population of grid cells: every region's population is split over the cells in proportion to the area of
the region that lies in each cell (equation 3 of the paper). Hand-built regions first, then the real data."""
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from census_analysis.cell_datasets import load_cell_population
from census_analysis.msoa_data import load_msoa_data
from census_analysis.population_data_processor.cell_matrix_population_calculator import (
    calculate_cell_matrix_population,
    split_population_by_overlapping_area,
)
from common.file_utils import load_dataframe_from_pickle
from common.path_configs import CELL_POPULATION_PATH

WEST_REGION, EAST_REGION = box(0.0, 0.0, 20.0, 10.0), box(20.0, 0.0, 40.0, 10.0)
REGION_POPULATIONS = np.array([100.0, 60.0])
FINE_CELL_SIZE_M = 100
FINE_CELLS_PER_PUBLISHED_CELL_SIDE = 5


def split(cells: list) -> np.ndarray:
    return split_population_by_overlapping_area(cells, [WEST_REGION, EAST_REGION], REGION_POPULATIONS)


def test_cells_inside_one_region_share_its_population_by_area():
    """Four 10 m cells in a row: each half of the west region holds 50 people, each half of the east 30."""
    cells = [box(0.0, 0.0, 10.0, 10.0), box(10.0, 0.0, 20.0, 10.0), box(20.0, 0.0, 30.0, 10.0), box(30.0, 0.0, 40.0, 10.0)]
    np.testing.assert_allclose(split(cells), [50.0, 50.0, 30.0, 30.0], rtol=1e-12)


def test_cell_across_two_regions_adds_both_shares():
    """Cell from 15 to 25 m: a quarter of the west region (25) plus a quarter of the east region (15)."""
    np.testing.assert_allclose(split([box(15.0, 0.0, 25.0, 10.0)]), [40.0], rtol=1e-12)


def test_cell_outside_every_region_or_only_touching_one_is_empty():
    np.testing.assert_array_equal(split([box(50.0, 0.0, 60.0, 10.0), box(40.0, 0.0, 50.0, 10.0)]), [0.0, 0.0])


def test_population_of_the_published_cells_is_the_stored_table():
    """The stored 500 m table was written by the published cell-by-cell calculation."""
    stored = load_dataframe_from_pickle(CELL_POPULATION_PATH).sort_values(["row", "col"]).reset_index(drop=True)
    computed = calculate_cell_matrix_population().sort_values(["row", "col"]).reset_index(drop=True)

    assert list(computed.columns) == list(stored.columns)
    assert computed[["row", "col"]].equals(stored[["row", "col"]])
    np.testing.assert_allclose(computed["population"], stored["population"], rtol=1e-9, atol=1e-9)
    assert computed["geometry"].iloc[0].equals(stored["geometry"].iloc[0])


def test_fine_cells_add_up_to_their_published_cell():
    """Splitting by area is additive: the 25 fine cells of a 500 m cell hold exactly its population."""
    fine = load_cell_population(FINE_CELL_SIZE_M)
    published = load_cell_population()
    parents = fine.assign(
        row=fine["row"] // FINE_CELLS_PER_PUBLISHED_CELL_SIDE, col=fine["col"] // FINE_CELLS_PER_PUBLISHED_CELL_SIDE
    ).groupby(["row", "col"], as_index=False)["population"].sum()
    merged = published.merge(parents, on=["row", "col"], suffixes=("_published", "_fine"), validate="1:1")

    assert len(merged) == len(published)
    np.testing.assert_allclose(merged["population_fine"], merged["population_published"], rtol=1e-9, atol=1e-6)


def test_fine_grid_loses_no_resident_of_the_published_grid_and_invents_none():
    total_residents = sum(load_msoa_data().msoa_populations.values())
    fine_total = load_cell_population(FINE_CELL_SIZE_M)["population"].sum()
    assert load_cell_population()["population"].sum() <= fine_total <= total_residents
    assert (total_residents - fine_total) / total_residents < 1e-4
