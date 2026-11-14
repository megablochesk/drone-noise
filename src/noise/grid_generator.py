import math
from dataclasses import dataclass, field

import geopandas as gpd
import shapely
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
    noise_history: list = field(default_factory=list)
    max_noise: float = 0.0

    def add_noise(self, noise_db: float):
        self.noise_history.append(noise_db)
        self.max_noise = max(self.max_noise, noise_db)


def load_and_reproject_geojson(file_path):
    df = gpd.read_file(file_path)
    return df.to_crs(epsg=27700)


def compute_grid_dimensions(cell_size=CELL_SIZE):
    rows = math.floor((BOUNDARIES.top - BOUNDARIES.bottom) / cell_size)
    cols = math.floor((BOUNDARIES.right - BOUNDARIES.left) / cell_size)

    return rows, cols


def create_grid(cell_size=CELL_SIZE):
    cells = []
    num_rows, num_cols = compute_grid_dimensions(cell_size)

    for r in range(num_rows):
        y = BOUNDARIES.bottom + r * cell_size
        for c in range(num_cols):
            x = BOUNDARIES.left + c * cell_size
            geometry = box(x, y, x + cell_size, y + cell_size)
            cells.append({
                "geometry": geometry,
                "row": r,
                "col": c
            })

    return cells


def filter_cells_in_polygon(cells, boundary_polygon):
    # A prepared polygon answers the intersection test from a spatial index instead of all its edges;
    # the index is only used when the prepared polygon is the one asked.
    shapely.prepare(boundary_polygon)

    return [cell for cell in cells if boundary_polygon.intersects(cell["geometry"])]


def get_valid_cells(cell_size=CELL_SIZE):
    df = load_and_reproject_geojson(LONDON_BOUNDARIES_PATH)
    boundary_polygon = df.geometry.unary_union

    all_cells = create_grid(cell_size)
    valid_cells = filter_cells_in_polygon(all_cells, boundary_polygon)

    return valid_cells


def build_cell_matrix(cell_size=CELL_SIZE):
    cells = get_valid_cells(cell_size)

    matrix = []
    for cell in cells:
        r, c = cell["row"], cell["col"]

        centroid = Coordinate(
            northing=BOUNDARIES.bottom + (r + 0.5) * cell_size,
            easting=BOUNDARIES.left + (c + 0.5) * cell_size
        )

        matrix.append(Cell(r, c, centroid))

    return matrix
