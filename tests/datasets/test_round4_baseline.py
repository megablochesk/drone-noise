"""Building the 500 m baseline from the Round 4 raster, on a hand-built raster and against the published file."""
import numpy as np
import pytest
from osgeo import gdal

from common.enum import LevelAveraging
from datasets.round4_baseline import (
    aggregate_raster_to_grid,
    build_baseline_table,
    build_cell_edges,
    read_raster_levels,
    write_baseline_file,
)
from noise.noise_data_processor import read_base_noise_data

NODATA_VALUE = -96.0
PUBLISHED_GRID_ROWS, PUBLISHED_GRID_COLUMNS = 90, 116
# North row first, as in a GeoTIFF: the 0 is a pixel below the reporting floor, the -96 an unmodelled one.
NORTH_FIRST_LEVELS = np.array([
    [46.0, 56.0, 66.0, 76.0],
    [44.0, 54.0, 64.0, 74.0],
    [42.0, 52.0, 62.0, NODATA_VALUE],
    [0.0, 50.0, 60.0, 70.0],
])


@pytest.fixture
def raster_path(tmp_path):
    """4 x 4 pixels of 10 m with the south-west corner at (1,005 m E, 2,005 m N)."""
    path = tmp_path / "raster.tif"
    dataset = gdal.GetDriverByName("GTiff").Create(str(path), 4, 4, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform((1_005.0, 10.0, 0.0, 2_045.0, 0.0, -10.0))
    band = dataset.GetRasterBand(1)
    band.SetNoDataValue(NODATA_VALUE)
    band.WriteArray(NORTH_FIRST_LEVELS.astype(np.float32))
    dataset.FlushCache()
    return path


def test_raster_is_read_with_ascending_northings(raster_path):
    raster = read_raster_levels(raster_path)
    np.testing.assert_array_equal(raster.levels_db, NORTH_FIRST_LEVELS[::-1])
    np.testing.assert_array_equal(raster.easting_edges_m, [1_005.0, 1_015.0, 1_025.0, 1_035.0, 1_045.0])
    np.testing.assert_array_equal(raster.northing_edges_m, [2_005.0, 2_015.0, 2_025.0, 2_035.0, 2_045.0])
    assert raster.nodata_value == NODATA_VALUE


def test_cell_edges_are_consecutive_cells_of_one_size():
    np.testing.assert_array_equal(build_cell_edges(100.0, 3, 500.0), [[100.0, 600.0], [600.0, 1_100.0], [1_100.0, 1_600.0]])


def test_raster_is_averaged_over_the_grid_with_the_floor_filled_in(raster_path):
    """2 x 2 cells of 20 m from (1,005, 2,005), 40 dB floor. South-west: (40 + 50 + 42 + 52) / 4 = 46 with the
    0 raised to 40; south-east: (60 + 70 + 62 + 40) / 4 = 58 with the unmodelled pixel at 40; north-west:
    (44 + 54 + 46 + 56) / 4 = 50; north-east: (64 + 74 + 66 + 76) / 4 = 70."""
    cell_levels = aggregate_raster_to_grid(
        read_raster_levels(raster_path), grid_west_m=1_005.0, grid_south_m=2_005.0, number_of_rows=2,
        number_of_columns=2, cell_size_m=20.0, floor_db=40.0, averaging=LevelAveraging.ARITHMETIC,
    )
    np.testing.assert_allclose(cell_levels, [[46.0, 58.0], [50.0, 70.0]], rtol=1e-12)


def test_baseline_table_lists_every_cell_of_the_bounding_grid_row_by_row():
    """2 rows x 3 columns of levels become six (row, col, noise_level) records, south row first."""
    table = build_baseline_table(np.array([[41.0, 42.0, 43.0], [51.0, 52.0, 53.0]]))
    assert table.to_dict("list") == {
        "row": [0, 0, 0, 1, 1, 1], "col": [0, 1, 2, 0, 1, 2], "noise_level": [41.0, 42.0, 43.0, 51.0, 52.0, 53.0],
    }


def test_written_baseline_is_read_by_the_baseline_reader(tmp_path):
    cell_levels = np.full((PUBLISHED_GRID_ROWS, PUBLISHED_GRID_COLUMNS), 47.25)
    cell_levels[3, 5] = 63.5
    baseline_path = tmp_path / "baseline.parquet"

    write_baseline_file(cell_levels, baseline_path)
    baseline = read_base_noise_data(str(baseline_path))

    assert list(baseline.columns) == ["row", "col", "noise_level"]
    assert len(baseline) == PUBLISHED_GRID_ROWS * PUBLISHED_GRID_COLUMNS
    assert baseline.loc[(baseline["row"] == 3) & (baseline["col"] == 5), "noise_level"].item() == 63.5
    assert baseline["noise_level"].value_counts()[47.25] == PUBLISHED_GRID_ROWS * PUBLISHED_GRID_COLUMNS - 1
