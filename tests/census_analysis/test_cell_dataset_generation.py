"""The generators of the derived cell datasets reproduce the stored files, so a missing file can be regenerated.

Cells are processed by a thread pool and come back in no fixed order, so tables are compared cell by cell.
The population table takes several minutes to compute and is not recomputed here.
"""
import pandas as pd
import pytest

from census_analysis.age_data_processor.age_cell_matrix_calculator import calculate_cell_matrix_age
from census_analysis.ethnicity_data_processor.ethnicity_cell_matrix_calculator import calculate_cell_matrix_ethnicity
from common.file_utils import load_dataframe_from_pickle
from common.path_configs import CELL_AGE_PATH, CELL_ETHNICITY_PATH

pytestmark = pytest.mark.slow
CELL_KEY = ["row", "col"]


def order_by_cell(dataset: pd.DataFrame) -> pd.DataFrame:
    return dataset.drop(columns="geometry").sort_values(CELL_KEY).reset_index(drop=True)


@pytest.mark.parametrize("calculate_dataset, stored_path", [
    (calculate_cell_matrix_age, CELL_AGE_PATH), (calculate_cell_matrix_ethnicity, CELL_ETHNICITY_PATH),
], ids=["age", "ethnicity"])
def test_recomputed_dataset_equals_the_stored_dataset(calculate_dataset, stored_path):
    recomputed, stored = calculate_dataset(), load_dataframe_from_pickle(stored_path)
    pd.testing.assert_frame_equal(order_by_cell(recomputed), order_by_cell(stored), check_exact=True)
    assert recomputed.attrs == stored.attrs
