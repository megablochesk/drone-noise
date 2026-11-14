"""The navigation grid of a baseline noise map, at the navigation cell size."""
from functools import lru_cache

import pandas as pd

from common.enum import BaselineNoiseMap
from common.model_configs import MapBoundaries, model_config
from noise.navigator.navigation_grid import NavigationGrid, build_navigation_grid
from noise.noise_data_processor import load_base_noise_data

NAVIGATION_CELL_SIZE_M = model_config.grid.nav_cell_m
HALF_CELL = 0.5


def build_navigation_grid_from_baseline(
        baseline: pd.DataFrame, cell_size_m: float, boundaries: MapBoundaries
) -> NavigationGrid:
    """One node per cell of the baseline table, at the cell centre."""
    rows, columns = baseline["row"].to_numpy(), baseline["col"].to_numpy()
    return build_navigation_grid(
        rows=rows, columns=columns,
        eastings=boundaries.left + (columns + HALF_CELL) * cell_size_m,
        northings=boundaries.bottom + (rows + HALF_CELL) * cell_size_m,
        noise_levels_db=baseline["noise_level"].to_numpy(dtype=float), cell_size_m=cell_size_m,
    )


@lru_cache(maxsize=None)
def load_navigation_grid(baseline_noise_map: BaselineNoiseMap) -> NavigationGrid:
    baseline = load_base_noise_data(baseline_noise_map, NAVIGATION_CELL_SIZE_M)
    return build_navigation_grid_from_baseline(baseline, NAVIGATION_CELL_SIZE_M, model_config.map_boundaries)
