"""Area-weighted averaging of a fine noise raster over grid cells.

All edges ascend; levels[i, j] is the pixel between northing edges i, i + 1 and easting edges j, j + 1.
Cells are given per axis as rows of (lower edge, upper edge).
"""
import numpy as np

from common.enum import LevelAveraging

COVERAGE_TOLERANCE_M = 1e-6


def fill_levels_below_floor(levels_db: np.ndarray, nodata_value: float, floor_db: float) -> np.ndarray:
    """Unmodelled pixels and pixels quieter than the floor (stored as 0 by the Round 4 maps) take the floor."""
    return np.where((levels_db == nodata_value) | (levels_db < floor_db), floor_db, levels_db)


def calculate_overlap_lengths(pixel_edges_m: np.ndarray, cell_edges_m: np.ndarray) -> np.ndarray:
    """Per cell (row) and pixel (column), the length in metres over which the two overlap along one axis."""
    overlap_starts_m = np.maximum(cell_edges_m[:, :1], pixel_edges_m[:-1])
    overlap_ends_m = np.minimum(cell_edges_m[:, 1:], pixel_edges_m[1:])
    return np.clip(overlap_ends_m - overlap_starts_m, 0.0, None)


def ensure_cells_inside_raster(overlap_lengths_m: np.ndarray, cell_edges_m: np.ndarray):
    cell_lengths_m = cell_edges_m[:, 1] - cell_edges_m[:, 0]
    if np.any(np.abs(overlap_lengths_m.sum(axis=1) - cell_lengths_m) > COVERAGE_TOLERANCE_M):
        raise ValueError("Some cells lie partly outside the raster")


def average_levels_over_cells(
        levels_db: np.ndarray,
        pixel_easting_edges_m: np.ndarray,
        pixel_northing_edges_m: np.ndarray,
        cell_easting_edges_m: np.ndarray,
        cell_northing_edges_m: np.ndarray,
        averaging: LevelAveraging,
) -> np.ndarray:
    """Average level of every (northing cell, easting cell) pair, each pixel weighted by its area in the cell."""
    easting_overlaps_m = calculate_overlap_lengths(pixel_easting_edges_m, cell_easting_edges_m)
    northing_overlaps_m = calculate_overlap_lengths(pixel_northing_edges_m, cell_northing_edges_m)
    ensure_cells_inside_raster(easting_overlaps_m, cell_easting_edges_m)
    ensure_cells_inside_raster(northing_overlaps_m, cell_northing_edges_m)

    uses_energy = averaging is LevelAveraging.ENERGY
    values = 10.0 ** (levels_db / 10.0) if uses_energy else levels_db.astype(np.float64)
    cell_areas_m2 = np.outer(northing_overlaps_m.sum(axis=1), easting_overlaps_m.sum(axis=1))
    averages = northing_overlaps_m @ values @ easting_overlaps_m.T / cell_areas_m2
    return 10.0 * np.log10(averages) if uses_energy else averages
