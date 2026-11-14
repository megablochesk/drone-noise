"""Exposure measured on the pixels of the baseline raster, with the drone level of the cell each pixel lies in.

This needs no averaging of the baseline, so it is the reference against which cell averages are judged.
Hand calculations: 10*log10(10^5.5 + 10^4) = 55.1352, 10*log10(10^5.5 + 10^5) = 56.1933,
10*log10(10^5.5 + 10^5.4) = 57.5390, 10*log10(10^5.5 + 10^6) = 61.1933.
"""
import numpy as np
import pytest

from metrics.pixel_exposure import map_pixels_to_cells, summarise_pixel_level_exposure

NO_CELL = -1


def test_pixels_are_assigned_to_the_grid_cell_that_holds_their_centre():
    """Two listed cells of 20 m, (row 0, column 0) and (row 1, column 1), from the origin; 10 m pixels with
    centres at 5, 15, 25, 35 m. Pixels in the other two quadrants belong to no listed cell."""
    centres_m = np.array([5.0, 15.0, 25.0, 35.0])
    cell_of_pixel = map_pixels_to_cells(
        pixel_easting_centres_m=centres_m, pixel_northing_centres_m=centres_m,
        cell_rows=np.array([0, 1]), cell_columns=np.array([0, 1]), grid_west_m=0.0, grid_south_m=0.0, cell_size_m=20.0,
    )
    np.testing.assert_array_equal(cell_of_pixel, [
        [0, 0, NO_CELL, NO_CELL],
        [0, 0, NO_CELL, NO_CELL],
        [NO_CELL, NO_CELL, 1, 1],
        [NO_CELL, NO_CELL, 1, 1],
    ])


def test_pixels_outside_the_grid_extent_belong_to_no_cell():
    cell_of_pixel = map_pixels_to_cells(
        pixel_easting_centres_m=np.array([-5.0, 5.0, 25.0]), pixel_northing_centres_m=np.array([5.0]),
        cell_rows=np.array([0]), cell_columns=np.array([0]), grid_west_m=0.0, grid_south_m=0.0, cell_size_m=20.0,
    )
    np.testing.assert_array_equal(cell_of_pixel, [[NO_CELL, 0, NO_CELL]])


def test_exposure_of_one_cell_with_four_pixels():
    """A 55 dB drone level over pixels at 40, 50, 54 and 60 dB raises them by 15.1352, 6.1933, 3.5390 and
    1.1933 dB (mean 6.5152). Three of the four pixels were below 55 dB and end above it, so three quarters
    of the cell's 400 residents are newly exposed; the 60 dB pixel was exposed already."""
    summary = summarise_pixel_level_exposure(
        drone_levels_db=np.array([55.0]), population=np.array([400.0]),
        pixel_levels_db=np.array([[40.0, 50.0], [54.0, 60.0]]), cell_of_pixel=np.array([[0, 0], [0, 0]]),
        threshold_db=55.0,
    )
    assert summary["mean_noise_increase_db"] == pytest.approx(6.5152, abs=1e-4)
    assert summary["newly_exposed_population_55db"] == pytest.approx(300.0)


def test_cells_count_by_their_pixels_and_unassigned_pixels_are_ignored():
    """Cell 0 has one pixel (40 dB) and no drone noise: no increase, nobody exposed. Cell 1 has two pixels at
    50 dB under a 55 dB drone level: +6.1933 dB each, all 100 residents newly exposed. The 90 dB pixel belongs
    to no cell. Mean over the three assigned pixels: 2 * 6.1933 / 3 = 4.1289 dB."""
    summary = summarise_pixel_level_exposure(
        drone_levels_db=np.array([-np.inf, 55.0]), population=np.array([70.0, 100.0]),
        pixel_levels_db=np.array([[40.0, 50.0], [50.0, 90.0]]), cell_of_pixel=np.array([[0, 1], [1, NO_CELL]]),
        threshold_db=55.0,
    )
    assert summary["mean_noise_increase_db"] == pytest.approx(4.1289, abs=1e-4)
    assert summary["newly_exposed_population_55db"] == pytest.approx(100.0)
