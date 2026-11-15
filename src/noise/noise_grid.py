from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from common.enum import BoundaryDatum
from noise.grid_generator import CELL_SIZE, PUBLISHED_BOUNDARY_DATUM, build_cell_matrix


@dataclass(frozen=True)
class NoiseGrid:
    """The noise cells inside the study boundary as aligned arrays, in the order of `build_cell_matrix`."""
    rows: np.ndarray
    columns: np.ndarray
    centroid_northings: np.ndarray
    centroid_eastings: np.ndarray


@lru_cache(maxsize=None)
def build_noise_grid_once(cell_size_m: int, boundary_datum: BoundaryDatum) -> NoiseGrid:
    cells = build_cell_matrix(cell_size_m, boundary_datum)
    return NoiseGrid(
        rows=np.array([cell.row for cell in cells], dtype=np.int64),
        columns=np.array([cell.column for cell in cells], dtype=np.int64),
        centroid_northings=np.array([cell.centroid.northing for cell in cells], dtype=np.float64),
        centroid_eastings=np.array([cell.centroid.easting for cell in cells], dtype=np.float64),
    )


def load_noise_grid(
        cell_size_m: int = CELL_SIZE, boundary_datum: BoundaryDatum = PUBLISHED_BOUNDARY_DATUM
) -> NoiseGrid:
    return build_noise_grid_once(cell_size_m, boundary_datum)


def to_grid_image(grid: NoiseGrid, values: np.ndarray) -> np.ndarray:
    """Cell values as a (row, column) image of the bounding grid; cells outside the study area are NaN."""
    image = np.full((grid.rows.max() + 1, grid.columns.max() + 1), np.nan)
    image[grid.rows, grid.columns] = values
    return image
