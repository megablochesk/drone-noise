from __future__ import annotations

from functools import partial
from typing import Dict, Tuple

import pandas as pd

from census_analysis.cell_matrix_calculator_utils import (
    calculate_cell_matrix_groups,
    calculate_cell_matrix_property,
    calculate_cell_property,
)
from census_analysis.dataset_loader import load_age_dataset_df
from census_analysis.msoa_cache import CachedMSOA, prepare_msoa_caches
from census_analysis.msoa_data import load_msoa_data
from common.enum import BoundaryDatum
from noise.grid_generator import CELL_SIZE, PUBLISHED_BOUNDARY_DATUM, get_valid_cells

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


def calculate_cell_matrix_age(
        cell_size: int = CELL_SIZE, boundary_datum: BoundaryDatum = PUBLISHED_BOUNDARY_DATUM,
        cells: list[dict] | None = None,
) -> pd.DataFrame:
    """The published grid keeps the published cell-by-cell calculation, which the stored table came from.

    `cells` are the grid cells to compute, every cell of the grid by default.
    """
    age_pivot, band_code_to_name = _build_age_pivot()
    if (cell_size, boundary_datum) != (CELL_SIZE, PUBLISHED_BOUNDARY_DATUM):
        fine_cell_matrix = calculate_cell_matrix_groups(age_pivot, cell_size, boundary_datum, cells)
        fine_cell_matrix.attrs[AGE_CODE_ATTRIBUTE] = band_code_to_name
        return fine_cell_matrix

    prepared = prepare_msoa_caches(age_pivot, load_msoa_data().msoa_index)

    cells = get_valid_cells() if cells is None else cells
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
