import math
from dataclasses import dataclass

import geopandas as gpd
from shapely.geometry import box

from common.coordinate import Coordinate
from common.model_configs import model_config
from common.path_configs import PATH_CONFIGS

BOUNDARIES = model_config.map_boundaries
CELL_SIZE = model_config.grid.noise_cell_m
LONDON_BOUNDARIES_PATH = PATH_CONFIGS.london_boundaries_path


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
    rows = math.floor((BOUNDARIES.top - BOUNDARIES.bottom) / CELL_SIZE)
    cols = math.floor((BOUNDARIES.right - BOUNDARIES.left) / CELL_SIZE)

    return rows, cols


def create_grid():
    cells = []
    num_rows, num_cols = compute_grid_dimensions()

    for r in range(num_rows):
        y = BOUNDARIES.bottom + r * CELL_SIZE
        for c in range(num_cols):
            x = BOUNDARIES.left + c * CELL_SIZE
            geometry = box(x, y, x + CELL_SIZE, y + CELL_SIZE)
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
            northing=BOUNDARIES.bottom + (r + 0.5) * CELL_SIZE,
            easting=BOUNDARIES.left + (c + 0.5) * CELL_SIZE
        )

        matrix.append(Cell(r, c, centroid))

    return matrix
