from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd

from census_analysis.cell_datasets import load_cell_population
from common.enum import BaselineNoiseMap, BoundaryDatum
from common.model_configs import PUBLISHED_BOUNDARY_DATUM
from noise.noise_data_processor import PUBLISHED_CELL_SIZE_M, load_base_noise_data
from noise.noise_grid import NoiseGrid, load_noise_grid


@dataclass(frozen=True)
class CellTable:
    """Baseline level and population of every noise cell, aligned with the noise grid."""
    rows: np.ndarray
    columns: np.ndarray
    baseline_levels_db: np.ndarray
    population: np.ndarray


def align_to_grid(grid: NoiseGrid, values: pd.DataFrame, value_column: str) -> np.ndarray:
    grid_cells = pd.DataFrame({"row": grid.rows, "col": grid.columns})
    merged = grid_cells.merge(values[["row", "col", value_column]], on=["row", "col"], how="left", validate="1:1")
    if merged[value_column].isna().any():
        raise ValueError(f"Some noise cells have no '{value_column}' value")
    return merged[value_column].to_numpy()


@lru_cache(maxsize=None)
def build_cell_table_once(
        baseline_noise_map: BaselineNoiseMap, cell_size_m: int, boundary_datum: BoundaryDatum
) -> CellTable:
    grid = load_noise_grid(cell_size_m, boundary_datum)
    return CellTable(
        rows=grid.rows,
        columns=grid.columns,
        baseline_levels_db=align_to_grid(grid, load_base_noise_data(baseline_noise_map, cell_size_m), "noise_level"),
        population=align_to_grid(grid, load_cell_population(cell_size_m, boundary_datum), "population"),
    )


def load_cell_table(
        baseline_noise_map: BaselineNoiseMap = BaselineNoiseMap.PUBLISHED, cell_size_m: int = PUBLISHED_CELL_SIZE_M,
        boundary_datum: BoundaryDatum = PUBLISHED_BOUNDARY_DATUM,
) -> CellTable:
    return build_cell_table_once(baseline_noise_map, cell_size_m, boundary_datum)
