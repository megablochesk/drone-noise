from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from noise.grid_generator import build_cell_matrix


@dataclass(frozen=True)
class NoiseGrid:
    """The noise cells inside the study boundary as aligned arrays, in the order of `build_cell_matrix`."""
    rows: np.ndarray
    columns: np.ndarray
    centroid_northings: np.ndarray
    centroid_eastings: np.ndarray


@lru_cache(maxsize=1)
def load_noise_grid() -> NoiseGrid:
    cells = build_cell_matrix()
    return NoiseGrid(
        rows=np.array([cell.row for cell in cells], dtype=np.int64),
        columns=np.array([cell.column for cell in cells], dtype=np.int64),
        centroid_northings=np.array([cell.centroid.northing for cell in cells], dtype=np.float64),
        centroid_eastings=np.array([cell.centroid.easting for cell in cells], dtype=np.float64),
    )
