"""Builds Round 4 baseline noise files (500 m by default) from the Defra road noise raster.

The file is a table with one record per cell of the bounding grid (row, col, noise_level), for any cell size
and for the arithmetic or the energy mean of the pixels.

Usage (from src/): python -m datasets.round4_baseline
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from osgeo import gdal

from common.enum import BaselineNoiseMap, LevelAveraging
from common.path_configs import PATH_CONFIGS, ROUND4_BASE_NOISE_PATH
from noise.baseline_aggregation import average_levels_over_cells, fill_levels_below_floor
from noise.grid_generator import BOUNDARIES, CELL_SIZE, compute_grid_dimensions
from noise.noise_data_processor import find_base_noise_path

gdal.UseExceptions()

# The Round 4 maps report nothing below 40 dB, and the published baseline used 40 dB where it had no data.
BASELINE_FLOOR_DB = 40.0
PARQUET_ENGINE = "fastparquet"
AVERAGING_OF_MAP = {
    BaselineNoiseMap.ROUND_4_ROAD: LevelAveraging.ARITHMETIC,
    BaselineNoiseMap.ROUND_4_ROAD_ENERGY: LevelAveraging.ENERGY,
}


@dataclass(frozen=True)
class RasterLevels:
    """Levels with ascending northings: levels_db[i, j] lies between northing edges i, i + 1 and easting edges j, j + 1."""
    levels_db: np.ndarray
    easting_edges_m: np.ndarray
    northing_edges_m: np.ndarray
    nodata_value: float


def read_raster_levels(raster_path: Path) -> RasterLevels:
    raster = gdal.Open(str(raster_path))
    band = raster.GetRasterBand(1)
    west_edge_m, pixel_width_m, _, north_edge_m, _, negative_pixel_height_m = raster.GetGeoTransform()
    south_edge_m = north_edge_m + raster.RasterYSize * negative_pixel_height_m
    return RasterLevels(
        levels_db=band.ReadAsArray()[::-1],
        easting_edges_m=west_edge_m + pixel_width_m * np.arange(raster.RasterXSize + 1),
        northing_edges_m=south_edge_m - negative_pixel_height_m * np.arange(raster.RasterYSize + 1),
        nodata_value=band.GetNoDataValue(),
    )


def build_cell_edges(first_edge_m: float, number_of_cells: int, cell_size_m: float) -> np.ndarray:
    lower_edges_m = first_edge_m + cell_size_m * np.arange(number_of_cells)
    return np.column_stack([lower_edges_m, lower_edges_m + cell_size_m])


def aggregate_raster_to_grid(
        raster: RasterLevels, grid_west_m: float, grid_south_m: float, number_of_rows: int, number_of_columns: int,
        cell_size_m: float, floor_db: float, averaging: LevelAveraging,
) -> np.ndarray:
    """Average level of every grid cell (row, column), rows counted from the south."""
    return average_levels_over_cells(
        fill_levels_below_floor(raster.levels_db, raster.nodata_value, floor_db),
        raster.easting_edges_m, raster.northing_edges_m,
        cell_easting_edges_m=build_cell_edges(grid_west_m, number_of_columns, cell_size_m),
        cell_northing_edges_m=build_cell_edges(grid_south_m, number_of_rows, cell_size_m),
        averaging=averaging,
    )


def build_baseline_table(cell_levels_db: np.ndarray) -> pd.DataFrame:
    """One record per cell of the bounding grid, south row first."""
    rows, columns = np.indices(cell_levels_db.shape)
    return pd.DataFrame({"row": rows.ravel(), "col": columns.ravel(), "noise_level": cell_levels_db.ravel()})


def write_baseline_file(cell_levels_db: np.ndarray, baseline_path: Path):
    build_baseline_table(cell_levels_db).to_parquet(baseline_path, engine=PARQUET_ENGINE, index=False)


def calculate_round4_cell_levels(
        averaging: LevelAveraging, floor_db: float = BASELINE_FLOOR_DB, cell_size_m: int = CELL_SIZE
) -> np.ndarray:
    number_of_rows, number_of_columns = compute_grid_dimensions(cell_size_m)
    return aggregate_raster_to_grid(
        read_raster_levels(Path(PATH_CONFIGS.round4_road_noise_raster_path)), BOUNDARIES.left, BOUNDARIES.bottom,
        number_of_rows, number_of_columns, cell_size_m, floor_db, averaging,
    )


def write_round4_baseline_file(
        baseline_noise_map: BaselineNoiseMap = BaselineNoiseMap.ROUND_4_ROAD, cell_size_m: int = CELL_SIZE
):
    cell_levels_db = calculate_round4_cell_levels(AVERAGING_OF_MAP[baseline_noise_map], cell_size_m=cell_size_m)
    write_baseline_file(cell_levels_db, Path(find_base_noise_path(baseline_noise_map, cell_size_m)))


def main():
    write_round4_baseline_file()
    print(f"baseline written to {ROUND4_BASE_NOISE_PATH}")


if __name__ == "__main__":
    main()
