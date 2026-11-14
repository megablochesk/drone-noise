"""Builds the 500 m baseline noise file from the Defra Round 4 road noise raster.

The file has the layout of the published baseline (one feature per cell of the bounding grid with row, col
and noise_level), so it can be read wherever the published one is.

Usage (from src/): python -m datasets.round4_baseline
"""
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from osgeo import gdal
from pyproj import Transformer

from common.enum import LevelAveraging
from common.path_configs import PATH_CONFIGS, ROUND4_BASE_NOISE_PATH
from noise.baseline_aggregation import average_levels_over_cells, fill_levels_below_floor
from noise.grid_generator import BOUNDARIES, CELL_SIZE, compute_grid_dimensions, create_grid

gdal.UseExceptions()

# The Round 4 maps report nothing below 40 dB, and the published baseline used 40 dB where it had no data.
BASELINE_FLOOR_DB = 40.0
GRID_CRS = "EPSG:27700"
FILE_CRS = "EPSG:4326"
COLLECTION_NAME = "regions_gdf_with_noise_levels"
COLLECTION_CRS = {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC::CRS84"}}


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


def build_cell_feature(cell: dict, noise_level_db: float, to_file_crs: Transformer) -> dict:
    longitudes, latitudes = to_file_crs.transform(*cell["geometry"].exterior.xy)
    return {
        "type": "Feature",
        "properties": {"row": cell["row"], "col": cell["col"], "noise_level": noise_level_db},
        "geometry": {"type": "Polygon", "coordinates": [[list(point) for point in zip(longitudes, latitudes)]]},
    }


def build_baseline_feature_collection(cell_levels_db: np.ndarray) -> dict:
    to_file_crs = Transformer.from_crs(GRID_CRS, FILE_CRS, always_xy=True)
    features = [
        build_cell_feature(cell, cell_levels_db[cell["row"], cell["col"]].item(), to_file_crs) for cell in create_grid()
    ]
    return {"type": "FeatureCollection", "name": COLLECTION_NAME, "crs": COLLECTION_CRS, "features": features}


def write_baseline_file(cell_levels_db: np.ndarray, baseline_path: Path):
    Path(baseline_path).write_text(json.dumps(build_baseline_feature_collection(cell_levels_db)))


def calculate_round4_cell_levels(averaging: LevelAveraging) -> np.ndarray:
    number_of_rows, number_of_columns = compute_grid_dimensions()
    return aggregate_raster_to_grid(
        read_raster_levels(Path(PATH_CONFIGS.round4_road_noise_raster_path)), BOUNDARIES.left, BOUNDARIES.bottom,
        number_of_rows, number_of_columns, CELL_SIZE, BASELINE_FLOOR_DB, averaging,
    )


def write_round4_baseline_file():
    """Arithmetic averaging, as the published baseline was aggregated from its 10 m data."""
    write_baseline_file(calculate_round4_cell_levels(LevelAveraging.ARITHMETIC), Path(ROUND4_BASE_NOISE_PATH))


def main():
    write_round4_baseline_file()
    print(f"baseline written to {ROUND4_BASE_NOISE_PATH}")


if __name__ == "__main__":
    main()
