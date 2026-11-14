"""Download Defra Round 4 road noise (LAeq,16h, all roads) for Greater London.

The coverage is fetched from the Defra WCS in 10 km tiles on the British National Grid, merged into one
GeoTIFF, and recorded with a checksum. Tiles already on disk are not fetched again.

Usage (from src/): python -m datasets.download_round4_road_noise [output_directory]
"""
from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests
from osgeo import gdal

from common.checksum import calculate_sha256
from common.path_configs import PATH_CONFIGS

gdal.UseExceptions()

WCS_URL = "https://environment.data.gov.uk/spatialdata/road-noise-all-metrics-england-round-4/wcs"
COVERAGE_ID = "562c9d56-7c2d-4d42-83bb-578d6e97a517__Road_Noise_LAeq16hr_England_Round_4_All"
WCS_VERSION = "2.0.1"
GEOTIFF_FORMAT = "image/tiff"

# Greater London study box, rounded outwards to whole tiles (metres, EPSG:27700).
WEST_EASTING_M = 500_000
EAST_EASTING_M = 570_000
SOUTH_NORTHING_M = 150_000
NORTH_NORTHING_M = 210_000
TILE_SIZE_M = 10_000

# The map reports levels from 40 dB upwards; quieter pixels are stored as 0.
REPORTING_FLOOR_DB = 40.0

REQUEST_TIMEOUT_S = 180
MAXIMUM_ATTEMPTS = 3
PAUSE_BETWEEN_ATTEMPTS_S = 10
MERGED_CREATION_OPTIONS = ["COMPRESS=DEFLATE", "TILED=YES"]
PROVENANCE_SUFFIX = ".provenance.json"


@dataclass(frozen=True)
class TileBounds:
    west_m: int
    south_m: int
    east_m: int
    north_m: int

    @property
    def file_name(self) -> str:
        return f"road_noise_laeq16h_r4_{self.west_m}_{self.south_m}.tif"


def build_tile_bounds() -> list[TileBounds]:
    return [
        TileBounds(west_m, south_m, west_m + TILE_SIZE_M, south_m + TILE_SIZE_M)
        for south_m in range(SOUTH_NORTHING_M, NORTH_NORTHING_M, TILE_SIZE_M)
        for west_m in range(WEST_EASTING_M, EAST_EASTING_M, TILE_SIZE_M)
    ]


def parse_axis_labels(describe_coverage_xml: str) -> tuple[str, str]:
    match = re.search(r'axisLabels="([^"]+)"', describe_coverage_xml)
    if match is None:
        raise ValueError("DescribeCoverage response has no axisLabels attribute")
    easting_label, northing_label = match.group(1).split()[:2]
    return easting_label, northing_label


def fetch_axis_labels(session: requests.Session) -> tuple[str, str]:
    parameters = {
        "service": "WCS",
        "version": WCS_VERSION,
        "request": "DescribeCoverage",
        "coverageId": COVERAGE_ID,
    }
    response = session.get(WCS_URL, params=parameters, timeout=REQUEST_TIMEOUT_S)
    response.raise_for_status()
    return parse_axis_labels(response.text)


def build_coverage_parameters(tile: TileBounds, axis_labels: tuple[str, str]) -> list[tuple[str, str]]:
    easting_label, northing_label = axis_labels
    return [
        ("service", "WCS"),
        ("version", WCS_VERSION),
        ("request", "GetCoverage"),
        ("coverageId", COVERAGE_ID),
        ("format", GEOTIFF_FORMAT),
        ("subset", f"{easting_label}({tile.west_m},{tile.east_m})"),
        ("subset", f"{northing_label}({tile.south_m},{tile.north_m})"),
    ]


def request_tile(session: requests.Session, parameters: list[tuple[str, str]]) -> bytes:
    response = session.get(WCS_URL, params=parameters, timeout=REQUEST_TIMEOUT_S)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    if "tiff" not in content_type:
        raise ValueError(f"Expected a GeoTIFF, got {content_type}: {response.text[:300]}")
    return response.content


def request_tile_with_retries(session: requests.Session, parameters: list[tuple[str, str]]) -> bytes:
    for attempt_number in range(1, MAXIMUM_ATTEMPTS + 1):
        try:
            return request_tile(session, parameters)
        except (requests.RequestException, ValueError) as error:
            if attempt_number == MAXIMUM_ATTEMPTS:
                raise
            print(f"  attempt {attempt_number} failed ({error}); retrying")
            time.sleep(PAUSE_BETWEEN_ATTEMPTS_S)
    raise RuntimeError("unreachable")


def download_tile(
        session: requests.Session, tile: TileBounds, axis_labels: tuple[str, str], tile_directory: Path
) -> Path:
    tile_path = tile_directory / tile.file_name
    if tile_path.exists():
        return tile_path
    print(f"Fetching {tile.file_name}")
    parameters = build_coverage_parameters(tile, axis_labels)
    tile_path.write_bytes(request_tile_with_retries(session, parameters))
    return tile_path


def download_tiles(tile_directory: Path) -> list[Path]:
    tile_directory.mkdir(parents=True, exist_ok=True)
    tiles = build_tile_bounds()
    with requests.Session() as session:
        axis_labels = fetch_axis_labels(session)
        print(f"Axis labels: {axis_labels}; {len(tiles)} tiles to fetch")
        return [download_tile(session, tile, axis_labels, tile_directory) for tile in tiles]


def merge_tiles(tile_paths: list[Path], merged_path: Path) -> dict:
    mosaic = gdal.BuildVRT("", [str(tile_path) for tile_path in tile_paths])
    gdal.Translate(str(merged_path), mosaic, creationOptions=MERGED_CREATION_OPTIONS).FlushCache()
    return summarise_raster(merged_path)


def summarise_raster(raster_path: Path) -> dict:
    raster = gdal.Open(str(raster_path))
    band = raster.GetRasterBand(1)
    west_edge_m, pixel_width_m, _, north_edge_m, _, negative_pixel_height_m = raster.GetGeoTransform()
    levels = band.ReadAsArray()
    has_data = levels != band.GetNoDataValue()
    is_reported = has_data & (levels >= REPORTING_FLOOR_DB)
    return {
        "crs": raster.GetProjection(),
        "pixel_size_m": [pixel_width_m, -negative_pixel_height_m],
        "west_edge_m": west_edge_m,
        "north_edge_m": north_edge_m,
        "width_pixels": raster.RasterXSize,
        "height_pixels": raster.RasterYSize,
        "nodata_value": band.GetNoDataValue(),
        "share_of_pixels_without_data": 1.0 - np.mean(has_data).item(),
        "share_of_pixels_below_reporting_floor": np.mean(has_data & ~is_reported).item(),
        "minimum_reported_level_db": levels[is_reported].min().item(),
        "maximum_level_db": levels[is_reported].max().item(),
    }


def write_provenance(merged_path: Path, raster_summary: dict):
    provenance = {
        "dataset": "Road Noise - All Metrics - England Round 4 (Defra)",
        "service_url": WCS_URL,
        "coverage_id": COVERAGE_ID,
        "bounding_box_epsg27700_m": [WEST_EASTING_M, SOUTH_NORTHING_M, EAST_EASTING_M, NORTH_NORTHING_M],
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "file": merged_path.name,
        "sha256": calculate_sha256(merged_path),
        "raster": raster_summary,
    }
    merged_path.with_suffix(PROVENANCE_SUFFIX).write_text(json.dumps(provenance, indent=2))


def main():
    merged_path = Path(PATH_CONFIGS.round4_road_noise_raster_path)
    output_directory = Path(sys.argv[1]) if len(sys.argv) > 1 else merged_path.parent
    tile_paths = download_tiles(output_directory / "tiles")
    raster_summary = merge_tiles(tile_paths, output_directory / merged_path.name)
    write_provenance(output_directory / merged_path.name, raster_summary)
    print(json.dumps(raster_summary, indent=2))


if __name__ == "__main__":
    main()
