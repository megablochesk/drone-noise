"""Averaging a fine noise raster over grid cells of any size. Expected values are hand calculations.

Convention: all edges ascend, and levels[i, j] is the pixel between northing edges i, i + 1 and easting
edges j, j + 1.
"""
import numpy as np
import pytest

from common.enum import LevelAveraging
from noise.baseline_aggregation import (
    average_levels_over_cells,
    calculate_overlap_lengths,
    fill_levels_below_floor,
)

TEN_METRE_EDGES = np.array([0.0, 10.0, 20.0, 30.0, 40.0])
LEVELS = np.array([
    [40.0, 50.0, 60.0, 70.0],
    [42.0, 52.0, 62.0, 72.0],
    [44.0, 54.0, 64.0, 74.0],
    [46.0, 56.0, 66.0, 76.0],
])


def test_overlap_of_cells_with_pixels_is_measured_in_metres():
    """Cell 5-25 m covers half of pixel one, all of pixel two, half of pixel three; cell 30-40 m is pixel four."""
    overlaps = calculate_overlap_lengths(TEN_METRE_EDGES, np.array([[5.0, 25.0], [30.0, 40.0]]))
    np.testing.assert_array_equal(overlaps, [[5.0, 10.0, 5.0, 0.0], [0.0, 0.0, 0.0, 10.0]])


def test_unmodelled_and_quiet_pixels_take_the_floor_level():
    """-96 marks unmodelled pixels, 0 marks pixels below the reporting floor; 39.5 is below a 40 dB floor too."""
    levels = np.array([[-96.0, 0.0, 39.5], [40.0, 55.25, 86.5]])
    filled = fill_levels_below_floor(levels, nodata_value=-96.0, floor_db=40.0)
    np.testing.assert_array_equal(filled, [[40.0, 40.0, 40.0], [40.0, 55.25, 86.5]])
    assert levels[0, 0] == -96.0


def test_arithmetic_average_of_whole_pixels():
    """2 x 2 cells of 2 x 2 pixels: south-west (40 + 50 + 42 + 52) / 4 = 46, north-east (64 + 74 + 66 + 76) / 4 = 70."""
    cell_edges = np.array([[0.0, 20.0], [20.0, 40.0]])
    averages = average_levels_over_cells(
        LEVELS, TEN_METRE_EDGES, TEN_METRE_EDGES, cell_edges, cell_edges, LevelAveraging.ARITHMETIC
    )
    np.testing.assert_allclose(averages, [[46.0, 66.0], [50.0, 70.0]], rtol=1e-12)


def test_partly_covered_pixels_count_by_their_covered_area():
    """Cell 5-25 m east, 0-10 m north: (5 * 40 + 10 * 50 + 5 * 60) / 20 = 50 dB."""
    averages = average_levels_over_cells(
        LEVELS, TEN_METRE_EDGES, TEN_METRE_EDGES,
        cell_easting_edges_m=np.array([[5.0, 25.0]]), cell_northing_edges_m=np.array([[0.0, 10.0]]),
        averaging=LevelAveraging.ARITHMETIC,
    )
    np.testing.assert_allclose(averages, [[50.0]], rtol=1e-12)


def test_energy_average_of_fifty_and_sixty_decibels():
    """10 * log10((10^5 + 10^6) / 2) = 57.4036 dB, against 55 dB for the arithmetic average."""
    levels = np.array([[50.0, 60.0]])
    edges = {"pixel_easting_edges_m": np.array([0.0, 10.0, 20.0]), "pixel_northing_edges_m": np.array([0.0, 10.0]),
             "cell_easting_edges_m": np.array([[0.0, 20.0]]), "cell_northing_edges_m": np.array([[0.0, 10.0]])}
    energy = average_levels_over_cells(levels, averaging=LevelAveraging.ENERGY, **edges)
    arithmetic = average_levels_over_cells(levels, averaging=LevelAveraging.ARITHMETIC, **edges)
    assert energy[0, 0] == pytest.approx(57.4036, abs=1e-4)
    assert arithmetic[0, 0] == pytest.approx(55.0, rel=1e-12)


@pytest.mark.parametrize("averaging", list(LevelAveraging))
def test_uniform_map_keeps_its_level_under_any_cell_layout(averaging):
    uniform = np.full((4, 4), 61.3)
    averages = average_levels_over_cells(
        uniform, TEN_METRE_EDGES, TEN_METRE_EDGES,
        cell_easting_edges_m=np.array([[3.0, 17.5], [17.5, 39.0]]), cell_northing_edges_m=np.array([[1.0, 38.0]]),
        averaging=averaging,
    )
    np.testing.assert_allclose(averages, 61.3, rtol=1e-12)


def test_cell_reaching_beyond_the_raster_is_an_error():
    with pytest.raises(ValueError, match="outside the raster"):
        average_levels_over_cells(
            LEVELS, TEN_METRE_EDGES, TEN_METRE_EDGES,
            cell_easting_edges_m=np.array([[30.0, 45.0]]), cell_northing_edges_m=np.array([[0.0, 10.0]]),
            averaging=LevelAveraging.ARITHMETIC,
        )
