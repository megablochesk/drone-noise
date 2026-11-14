"""Exposure measured on the pixels of the baseline raster, with the drone level of the cell each pixel lies in.

The drone level varies slowly over a cell, the baseline does not; evaluating the metrics pixel by pixel
therefore needs no averaging rule for the baseline and serves as the reference for cell-averaged baselines.
"""
import numpy as np

from metrics.exposure_metrics import calculate_mean_noise_increase_db, calculate_newly_exposed_population

NO_CELL = -1


def map_pixels_to_cells(
        pixel_easting_centres_m: np.ndarray, pixel_northing_centres_m: np.ndarray, cell_rows: np.ndarray,
        cell_columns: np.ndarray, grid_west_m: float, grid_south_m: float, cell_size_m: float,
) -> np.ndarray:
    """Per pixel (northing, easting), the position in the cell list of the cell holding its centre, or NO_CELL."""
    pixel_rows = np.floor((pixel_northing_centres_m - grid_south_m) / cell_size_m).astype(np.int64)
    pixel_columns = np.floor((pixel_easting_centres_m - grid_west_m) / cell_size_m).astype(np.int64)
    number_of_rows, number_of_columns = cell_rows.max() + 1, cell_columns.max() + 1

    cell_at = np.full((number_of_rows + 1, number_of_columns + 1), NO_CELL, dtype=np.int64)
    cell_at[cell_rows, cell_columns] = np.arange(len(cell_rows))
    inside_rows = (pixel_rows >= 0) & (pixel_rows < number_of_rows)
    inside_columns = (pixel_columns >= 0) & (pixel_columns < number_of_columns)
    return cell_at[np.where(inside_rows, pixel_rows, number_of_rows)[:, np.newaxis],
                   np.where(inside_columns, pixel_columns, number_of_columns)[np.newaxis, :]]


def summarise_pixel_level_exposure(
        drone_levels_db: np.ndarray, population: np.ndarray, pixel_levels_db: np.ndarray, cell_of_pixel: np.ndarray,
        threshold_db: float,
) -> dict:
    """Headline metrics over the assigned pixels; a cell's residents are spread evenly over its pixels."""
    is_assigned = cell_of_pixel != NO_CELL
    cells = cell_of_pixel[is_assigned]
    pixels_per_cell = np.bincount(cells, minlength=len(population))
    pixel_baseline_db, pixel_drone_db = pixel_levels_db[is_assigned], drone_levels_db[cells]
    pixel_population = population[cells] / pixels_per_cell[cells]
    return {
        "mean_noise_increase_db": calculate_mean_noise_increase_db(pixel_drone_db, pixel_baseline_db),
        "newly_exposed_population_55db": calculate_newly_exposed_population(
            pixel_drone_db, pixel_baseline_db, pixel_population, threshold_db
        ),
    }
