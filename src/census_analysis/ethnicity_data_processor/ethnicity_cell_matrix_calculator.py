from __future__ import annotations

from functools import partial

import pandas as pd

from census_analysis.cell_matrix_calculator_utils import calculate_cell_matrix_property, calculate_cell_property
from census_analysis.dataset_loader import load_ethnicity_dataset_df
from census_analysis.msoa_cache import CachedMSOA, prepare_msoa_caches
from census_analysis.msoa_data import MSOA_DATA
from noise.grid_generator import get_valid_cells

ETHNICITY_CODE_ATTRIBUTE = "ethnicity_code_to_name"

ETH_CODE_COL = "Ethnic group (20 categories) Code"
ETH_NAME_COL = "Ethnic group (20 categories)"
MSOA_CODE_COL = "Middle layer Super Output Areas Code"
VALUE_COL = "Observation"


def calculate_cell_matrix_ethnicity() -> pd.DataFrame:
    ethnicity_pivot, code_to_name = _build_ethnicity_pivot()
    prepared = prepare_msoa_caches(ethnicity_pivot, MSOA_DATA.msoa_index)

    cells = get_valid_cells()
    process_cell = partial(_annotate_cell_with_ethnicity, prepared=prepared)

    df = calculate_cell_matrix_property(cells, process_cell)
    df.attrs[("%s" % ETHNICITY_CODE_ATTRIBUTE)] = code_to_name
    return df



def _build_ethnicity_pivot():
    df = load_ethnicity_dataset_df()
    df = df[df[ETH_CODE_COL] >= 0]
    pivot = (
        df.pivot_table(
            index=MSOA_CODE_COL,
            columns=ETH_CODE_COL,
            values=VALUE_COL,
            aggfunc="sum",
            fill_value=0,
        )
        .astype(float)
        .sort_index()
    )
    code_to_name = (
        df[[ETH_CODE_COL, ETH_NAME_COL]]
        .drop_duplicates()
        .set_index(ETH_CODE_COL)[ETH_NAME_COL]
        .to_dict()
    )
    return pivot, code_to_name


def _annotate_cell_with_ethnicity(cell: dict, prepared: CachedMSOA) -> dict:
    totals = calculate_cell_property(cell["geometry"], prepared)
    result = dict(cell)

    for code in prepared.codes:
        result[int(code)] = totals[code]

    return result
