import math
import numpy as np
from dataclasses import dataclass
from numba import njit, prange
from tqdm import tqdm

from common.configuration import (
    MAP_LEFT, MAP_RIGHT, MAP_TOP, MAP_BOTTOM,
    NOISE_MATRIX_CELL_LENGTH, NOISE_MATRIX_CELL_WIDTH
)
from common.coordinate import Coordinate
from noise.noise_math_utils import (
    calculate_noise_at_distance,
    calculate_mixed_noise_level
)

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


@njit(parallel=True)
def calculate_cells_noise(rows, cols, cell_northings, cell_eastings, drone_northings, drone_eastings):
    total_noise_result = np.zeros((rows, cols), dtype=np.float64)
    max_noise_result = np.zeros((rows, cols), dtype=np.float64)
    for r in prange(rows):
        for c in prange(cols):
            centroid_n = cell_northings[r, c]
            centroid_e = cell_eastings[r, c]

            noises = np.empty(len(drone_northings), dtype=np.float64)
            for i in range(len(drone_northings)):
                dist = (centroid_n - drone_northings[i])**2 + (centroid_e - drone_eastings[i])**2
                noises[i] = calculate_noise_at_distance(dist)

            mixed_noise = calculate_mixed_noise_level(noises)
            total_noise_result[r, c] = mixed_noise
            max_noise_result[r, c] = mixed_noise
    return total_noise_result, max_noise_result


def compute_grid_dimensions():
    rows = math.floor((MAP_TOP - MAP_BOTTOM) / NOISE_MATRIX_CELL_WIDTH)
    cols = math.floor((MAP_RIGHT - MAP_LEFT) / NOISE_MATRIX_CELL_LENGTH)
    return rows, cols


def build_cell_matrix(rows, cols):
    matrix = []
    for r in range(rows):
        row_cells = []
        for c in range(cols):
            centroid = Coordinate(
                northing=MAP_TOP - (r + 0.5) * NOISE_MATRIX_CELL_WIDTH,
                easting=MAP_LEFT + (c + 0.5) * NOISE_MATRIX_CELL_LENGTH,
            )
            row_cells.append(Cell(r, c, centroid))
        matrix.append(row_cells)
    return matrix


def extract_cell_arrays(noise_matrix):
    rows = len(noise_matrix)
    cols = len(noise_matrix[0]) if rows > 0 else 0
    cell_northings = np.zeros((rows, cols), dtype=np.float64)
    cell_eastings = np.zeros((rows, cols), dtype=np.float64)
    for r in range(rows):
        for c in range(cols):
            cell_northings[r, c] = noise_matrix[r][c].centroid.northing
            cell_eastings[r, c] = noise_matrix[r][c].centroid.easting
    return cell_northings, cell_eastings


class NoiseTracker:
    def __init__(self):
        self.rows, self.cols = compute_grid_dimensions()
        self.drone_location_history = []
        self.noise_matrix = build_cell_matrix(self.rows, self.cols)

    def track_drones(self, drones):
        self.drone_location_history.append([drone.location for drone in drones])

    def calculate_noise_matrix(self):
        cell_northings, cell_eastings = extract_cell_arrays(self.noise_matrix)

        with tqdm(total=len(self.drone_location_history), desc="Calculating Noise Matrix", unit="iteration") as pbar:
            for drone_locations in self.drone_location_history:
                drone_northings = np.array([loc.northing for loc in drone_locations], dtype=np.float64)
                drone_eastings = np.array([loc.easting for loc in drone_locations], dtype=np.float64)

                total_noise, max_noise = calculate_cells_noise(
                    self.rows, self.cols,
                    cell_northings,
                    cell_eastings,
                    drone_northings,
                    drone_eastings
                )

                for r in range(self.rows):
                    for c in range(self.cols):
                        self.noise_matrix[r][c].add_noise(total_noise[r, c])
                        if max_noise[r, c] > self.noise_matrix[r][c].max_noise:
                            self.noise_matrix[r][c].max_noise = max_noise[r, c]

                pbar.update(1)
