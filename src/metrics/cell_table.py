from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd

from common.file_utils import load_dataframe_from_pickle
from common.path_configs import CELL_POPULATION_PATH
from noise.noise_data_processor import BASE_NOISE_DATA
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


@lru_cache(maxsize=1)
def load_cell_table() -> CellTable:
    grid = load_noise_grid()
    return CellTable(
        rows=grid.rows,
        columns=grid.columns,
        baseline_levels_db=align_to_grid(grid, BASE_NOISE_DATA, "noise_level"),
        population=align_to_grid(grid, load_dataframe_from_pickle(CELL_POPULATION_PATH), "population"),
    )
