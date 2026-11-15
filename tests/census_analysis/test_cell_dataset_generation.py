"""The generators of the derived cell datasets reproduce the stored files, so a missing file can be regenerated.

Cells are processed by a thread pool and come back in no fixed order, so tables are compared cell by cell.
The population table is recomputed against the stored file in test_cell_population.py.
"""
import pandas as pd
import pytest

from census_analysis.age_data_processor.age_cell_matrix_calculator import calculate_cell_matrix_age
from census_analysis.cell_datasets import load_cell_age, load_cell_ethnicity
from census_analysis.ethnicity_data_processor.ethnicity_cell_matrix_calculator import calculate_cell_matrix_ethnicity
from common.file_utils import load_dataframe_from_pickle
from common.path_configs import CELL_AGE_PATH, CELL_ETHNICITY_PATH
from noise.grid_generator import get_valid_cells

CELL_KEY = ["row", "col"]
# Every 25th cell of the 500 m grid in grid order: 267 cells spread over the whole study area.
SAMPLED_CELL_STRIDE = 25
FINE_CELL_SIZE_M = 100
# Every 500th row of the stored 100 m table: 323 cells.
SAMPLED_FINE_CELL_STRIDE = 500
FINE_RELATIVE_TOLERANCE = 1e-12
GENERATORS = [(calculate_cell_matrix_age, CELL_AGE_PATH), (calculate_cell_matrix_ethnicity, CELL_ETHNICITY_PATH)]


def order_by_cell(dataset: pd.DataFrame) -> pd.DataFrame:
    return dataset.drop(columns="geometry").sort_values(CELL_KEY).reset_index(drop=True)


@pytest.mark.parametrize("calculate_dataset, stored_path", GENERATORS, ids=["age", "ethnicity"])
def test_recomputed_sample_of_cells_equals_the_stored_dataset(calculate_dataset, stored_path):
    """The published cell-by-cell calculation for a fixed sample of cells gives their stored rows exactly."""
    sampled_cells = get_valid_cells()[::SAMPLED_CELL_STRIDE]
    recomputed, stored = calculate_dataset(cells=sampled_cells), load_dataframe_from_pickle(stored_path)
    stored_sample = stored.merge(recomputed[CELL_KEY], on=CELL_KEY, validate="1:1")

    assert len(recomputed) == len(sampled_cells)
    pd.testing.assert_frame_equal(order_by_cell(recomputed), order_by_cell(stored_sample), check_exact=True)
    assert recomputed.attrs == stored.attrs


@pytest.mark.parametrize("calculate_dataset, load_stored_dataset", [
    (calculate_cell_matrix_age, load_cell_age), (calculate_cell_matrix_ethnicity, load_cell_ethnicity),
], ids=["age", "ethnicity"])
def test_recomputed_sample_of_fine_cells_equals_the_stored_fine_dataset(calculate_dataset, load_stored_dataset):
    """The one-pass calculation of the fine grid, for a fixed sample of its cells, gives their stored rows.

    The sampled cells are taken from the stored table: building the whole 100 m grid would take most of the time.
    """
    stored = load_stored_dataset(FINE_CELL_SIZE_M)
    stored_sample = stored.iloc[::SAMPLED_FINE_CELL_STRIDE]
    sampled_cells = stored_sample[["geometry", *CELL_KEY]].to_dict("records")

    recomputed = calculate_dataset(FINE_CELL_SIZE_M, cells=sampled_cells)

    assert list(zip(recomputed["row"], recomputed["col"])) == [(cell["row"], cell["col"]) for cell in sampled_cells]
    pd.testing.assert_frame_equal(
        order_by_cell(recomputed), order_by_cell(stored_sample[recomputed.columns]), rtol=FINE_RELATIVE_TOLERANCE
    )
    assert recomputed.attrs == stored.attrs


@pytest.mark.slow
@pytest.mark.parametrize("calculate_dataset, stored_path", GENERATORS, ids=["age", "ethnicity"])
def test_recomputed_dataset_equals_the_stored_dataset(calculate_dataset, stored_path):
    recomputed, stored = calculate_dataset(), load_dataframe_from_pickle(stored_path)
    pd.testing.assert_frame_equal(order_by_cell(recomputed), order_by_cell(stored), check_exact=True)
    assert recomputed.attrs == stored.attrs
