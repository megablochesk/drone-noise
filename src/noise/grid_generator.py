import math
from dataclasses import dataclass

import geopandas as gpd
from common.configuration import (
    MAP_LEFT, MAP_RIGHT, MAP_TOP, MAP_BOTTOM,
    NOISE_MATRIX_CELL_LENGTH, NOISE_MATRIX_CELL_WIDTH,
    LONDON_BOUNDARIES_PATH
)
from common.coordinate import Coordinate
from shapely.geometry import box


@dataclass
class Cell:
    row: int
    column: int
    centroid: Coordinate
    total_noise: float = 0
    max_noise: float = 0

    def add_noise(self, noise: float) -> None:
        self.total_noise += noise
        self.max_noise = max(self.max_noise, noise)


def load_and_reproject_geojson(file_path):
    df = gpd.read_file(file_path)
    return df.to_crs(epsg=27700)


def compute_grid_dimensions():
    rows = math.floor((MAP_TOP - MAP_BOTTOM) / NOISE_MATRIX_CELL_WIDTH)
    cols = math.floor((MAP_RIGHT - MAP_LEFT) / NOISE_MATRIX_CELL_LENGTH)

    return rows, cols


def create_grid():
    cells = []
    num_rows, num_cols = compute_grid_dimensions()

    for r in range(num_rows):
        y = MAP_BOTTOM + r * NOISE_MATRIX_CELL_LENGTH
        for c in range(num_cols):
            x = MAP_LEFT + c * NOISE_MATRIX_CELL_WIDTH
            geometry = box(x, y, x + NOISE_MATRIX_CELL_WIDTH, y + NOISE_MATRIX_CELL_LENGTH)
            cells.append({
                "geometry": geometry,
                "row": r,
                "col": c
            })

    return cells


def filter_cells_in_polygon(cells, boundary_polygon):
    return [cell for cell in cells if cell["geometry"].intersects(boundary_polygon)]


def get_valid_cells():
    df = load_and_reproject_geojson(LONDON_BOUNDARIES_PATH)
    boundary_polygon = df.geometry.unary_union

    all_cells = create_grid()
    valid_cells = filter_cells_in_polygon(all_cells, boundary_polygon)

    return valid_cells


def build_cell_matrix():
    cells = get_valid_cells()

    matrix = []
    for cell in cells:
        r, c = cell["row"], cell["col"]

        centroid = Coordinate(
            northing=MAP_BOTTOM + (r + 0.5) * NOISE_MATRIX_CELL_WIDTH,
            easting=MAP_LEFT + (c + 0.5) * NOISE_MATRIX_CELL_LENGTH,
        )

        matrix.append(Cell(r, c, centroid))

    return matrix
