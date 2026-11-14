"""Download of the Defra Round 4 road noise map: tiling, requests and merging, without touching the network.

Facts about the service used below were read from its DescribeCoverage response and from one downloaded
tile: axis labels "E N", 10 m pixels whose edges lie on ...5 m, levels from 40 dB upwards in 0.01 dB steps,
0 for pixels below 40 dB and -96 where nothing was modelled.
"""
import numpy as np
import pytest
import requests
from osgeo import gdal

from datasets.download_round4_road_noise import (
    COVERAGE_ID,
    TileBounds,
    build_coverage_parameters,
    build_tile_bounds,
    download_tile,
    merge_tiles,
    parse_axis_labels,
    request_tile,
    request_tile_with_retries,
    summarise_raster,
)

DESCRIBE_COVERAGE_EXCERPT = """
<gml:Envelope srsName="http://www.opengis.net/def/crs/EPSG/0/27700" axisLabels="E N" uomLabels="m m" srsDimension="2">
<gml:RectifiedGrid dimension="2"><gml:axisLabels>i j</gml:axisLabels>
"""
TILE = TileBounds(west_m=530_000, south_m=180_000, east_m=540_000, north_m=190_000)
PIXEL_SIZE_M = 10.0
NODATA_VALUE = -96.0


class FakeResponse:
    def __init__(self, content: bytes = b"tiff bytes", content_type: str = "image/tiff", status_error: Exception | None = None):
        self.content, self.text, self.headers = content, content.decode(errors="replace"), {"Content-Type": content_type}
        self.status_error = status_error

    def raise_for_status(self):
        if self.status_error is not None:
            raise self.status_error


class FakeSession:
    """Answers each request with the next prepared response and remembers what was asked."""

    def __init__(self, responses: list[FakeResponse]):
        self.responses, self.requested_parameters = list(responses), []

    def get(self, url, params, timeout):
        self.requested_parameters.append(params)
        return self.responses.pop(0)


def write_tile(path, west_edge_m: float, north_edge_m: float, levels: np.ndarray):
    rows, columns = levels.shape
    dataset = gdal.GetDriverByName("GTiff").Create(str(path), columns, rows, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform((west_edge_m, PIXEL_SIZE_M, 0.0, north_edge_m, 0.0, -PIXEL_SIZE_M))
    band = dataset.GetRasterBand(1)
    band.SetNoDataValue(NODATA_VALUE)
    band.WriteArray(levels.astype(np.float32))
    dataset.FlushCache()


def test_study_box_is_cut_into_forty_two_ten_kilometre_tiles():
    """500-570 km east and 150-210 km north: 7 x 6 tiles, south-west corner first."""
    tiles = build_tile_bounds()
    assert len(tiles) == 42
    assert tiles[0] == TileBounds(500_000, 150_000, 510_000, 160_000)
    assert tiles[-1] == TileBounds(560_000, 200_000, 570_000, 210_000)
    assert {(tile.east_m - tile.west_m, tile.north_m - tile.south_m) for tile in tiles} == {(10_000, 10_000)}
    assert len({(tile.west_m, tile.south_m) for tile in tiles}) == 42


def test_tile_file_is_named_after_its_south_west_corner():
    assert TILE.file_name == "road_noise_laeq16h_r4_530000_180000.tif"


def test_axis_labels_are_read_from_the_envelope_not_from_the_grid():
    assert parse_axis_labels(DESCRIBE_COVERAGE_EXCERPT) == ("E", "N")


def test_response_without_axis_labels_is_rejected():
    with pytest.raises(ValueError, match="axisLabels"):
        parse_axis_labels("<gml:Envelope srsDimension='2'>")


def test_coverage_request_subsets_both_axes_to_the_tile():
    parameters = build_coverage_parameters(TILE, ("E", "N"))
    assert ("subset", "E(530000,540000)") in parameters
    assert ("subset", "N(180000,190000)") in parameters
    assert ("coverageId", COVERAGE_ID) in parameters
    assert ("request", "GetCoverage") in parameters and ("format", "image/tiff") in parameters


def test_answer_that_is_not_a_geotiff_is_rejected():
    """The service reports errors as XML with status 200."""
    session = FakeSession([FakeResponse(b"<ows:ExceptionReport/>", content_type="application/xml")])
    with pytest.raises(ValueError, match="Expected a GeoTIFF"):
        request_tile(session, [])


def test_failed_request_is_repeated_and_the_last_failure_is_raised(monkeypatch):
    monkeypatch.setattr("datasets.download_round4_road_noise.PAUSE_BETWEEN_ATTEMPTS_S", 0)
    failing_once = FakeSession([FakeResponse(status_error=requests.ConnectionError("reset")), FakeResponse(b"tile")])
    assert request_tile_with_retries(failing_once, []) == b"tile"

    always_failing = FakeSession([FakeResponse(status_error=requests.ConnectionError("reset"))] * 3)
    with pytest.raises(requests.ConnectionError):
        request_tile_with_retries(always_failing, [])
    assert len(always_failing.requested_parameters) == 3


def test_tile_that_is_already_on_disk_is_not_requested_again(tmp_path):
    (tmp_path / TILE.file_name).write_bytes(b"earlier download")
    session = FakeSession([])
    assert download_tile(session, TILE, ("E", "N"), tmp_path) == tmp_path / TILE.file_name
    assert session.requested_parameters == []
    assert (tmp_path / TILE.file_name).read_bytes() == b"earlier download"


def test_missing_tile_is_requested_and_written(tmp_path):
    session = FakeSession([FakeResponse(b"new tile")])
    tile_path = download_tile(session, TILE, ("E", "N"), tmp_path)
    assert tile_path.read_bytes() == b"new tile"
    assert ("subset", "E(530000,540000)") in session.requested_parameters[0]


def test_neighbouring_tiles_are_merged_into_one_raster(tmp_path):
    """Two 2 x 2 tiles side by side: the mosaic is 2 x 4 pixels and keeps every level, the 0 and the -96."""
    west_levels = np.array([[40.0, 55.5], [0.0, 61.25]])
    east_levels = np.array([[70.0, NODATA_VALUE], [45.5, 86.5]])
    write_tile(tmp_path / "west.tif", 1_005.0, 2_025.0, west_levels)
    write_tile(tmp_path / "east.tif", 1_025.0, 2_025.0, east_levels)

    summary = merge_tiles([tmp_path / "west.tif", tmp_path / "east.tif"], tmp_path / "merged.tif")

    merged = gdal.Open(str(tmp_path / "merged.tif"))
    np.testing.assert_array_equal(merged.GetRasterBand(1).ReadAsArray(), np.hstack([west_levels, east_levels]).astype(np.float32))
    assert merged.GetGeoTransform() == (1_005.0, 10.0, 0.0, 2_025.0, 0.0, -10.0)
    assert (summary["width_pixels"], summary["height_pixels"]) == (4, 2)


def test_raster_summary_separates_unmodelled_pixels_and_pixels_below_the_reporting_floor(tmp_path):
    """Eight pixels: one unmodelled (-96), two below the 40 dB floor (0), five levels from 40.0 to 86.5 dB."""
    levels = np.array([[40.0, 55.5, 70.0, NODATA_VALUE], [0.0, 61.25, 0.0, 86.5]])
    write_tile(tmp_path / "tile.tif", 1_005.0, 2_025.0, levels)

    summary = summarise_raster(tmp_path / "tile.tif")

    assert summary["pixel_size_m"] == [10.0, 10.0]
    assert summary["west_edge_m"] == 1_005.0 and summary["north_edge_m"] == 2_025.0
    assert summary["nodata_value"] == NODATA_VALUE
    assert summary["share_of_pixels_without_data"] == pytest.approx(1 / 8)
    assert summary["share_of_pixels_below_reporting_floor"] == pytest.approx(2 / 8)
    assert summary["minimum_reported_level_db"] == pytest.approx(40.0)
    assert summary["maximum_level_db"] == pytest.approx(86.5)
