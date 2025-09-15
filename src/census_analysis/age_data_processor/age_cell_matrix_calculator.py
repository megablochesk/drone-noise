from __future__ import annotations

from functools import partial
from typing import Dict, Tuple

import pandas as pd

from census_analysis.cell_matrix_calculator_utils import calculate_cell_matrix_property, calculate_cell_property
from census_analysis.dataset_loader import load_age_dataset_df
from census_analysis.msoa_cache import CachedMSOA, prepare_msoa_caches
from census_analysis.msoa_data import MSOA_DATA
from noise.grid_generator import get_valid_cells

AGE_CODE_ATTRIBUTE = "age_code_to_name"

MSOA_CODE_COL = "Middle layer Super Output Areas Code"
AGE_CODE_COL = "Age (101 categories) Code"
VALUE_COL = "Observation"


AGE_BAND_DEFS: Dict[int, Tuple[int, int, str]] = {
    0: (0, 15, "0–15"),
    1: (16, 24, "16–24"),
    2: (25, 44, "25–44"),
    3: (45, 64, "45–64"),
    4: (65, 100, "65+"),
}


def calculate_cell_matrix_age() -> pd.DataFrame:
    age_pivot, band_code_to_name = _build_age_pivot()
    prepared = prepare_msoa_caches(age_pivot, MSOA_DATA.msoa_index)

    cells = get_valid_cells()
    process_cell = partial(_annotate_cell_with_age, prepared=prepared)

    df = calculate_cell_matrix_property(cells, process_cell)
    df.attrs[AGE_CODE_ATTRIBUTE] = band_code_to_name
    return df


def _build_age_pivot() -> Tuple[pd.DataFrame, Dict[int, str]]:
    df = load_age_dataset_df()
    df = df[df[AGE_CODE_COL] >= 0]

    def _to_band(age_code: int) -> int:
        a = int(age_code)
        if a <= 15:
            return 0
        if a <= 24:
            return 1
        if a <= 44:
            return 2
        if a <= 64:
            return 3
        return 4

    df = df.assign(age_band_id=df[AGE_CODE_COL].astype(int).map(_to_band))

    pivot = (
        df.pivot_table(
            index=MSOA_CODE_COL,
            columns="age_band_id",
            values=VALUE_COL,
            aggfunc="sum",
            fill_value=0,
        )
        .astype(float)
        .sort_index()
    )

    pivot = pivot.reindex(columns=[0, 1, 2, 3, 4], fill_value=0.0)

    band_code_to_name = {bid: label for bid, (_, _, label) in AGE_BAND_DEFS.items()}
    return pivot, band_code_to_name


def _annotate_cell_with_age(cell: dict, prepared: CachedMSOA) -> dict:
    totals = calculate_cell_property(cell["geometry"], prepared)
    out = dict(cell)
    for code in prepared.codes:
        out[code] = totals[code]
    return out
