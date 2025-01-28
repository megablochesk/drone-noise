import numpy as np
from noise.grid_generator import compute_grid_dimensions, build_cell_matrix
from noise.noise_math_utils import calculate_noise_at_distance, calculate_mixed_noise_level

from numba import njit, prange
from tqdm import tqdm


@njit(parallel=True)
def calculate_cells_noise(cell_northings, cell_eastings, drone_northings, drone_eastings):
    num_cells = len(cell_northings)
    num_drones = len(drone_northings)

    total_noise_result = np.zeros(num_cells, dtype=np.float64)

    for i in prange(num_cells):
        centroid_n = cell_northings[i]
        centroid_e = cell_eastings[i]

        noises = np.empty(num_drones, dtype=np.float64)
        for j in range(num_drones):
            dist = (centroid_n - drone_northings[j]) ** 2 + (centroid_e - drone_eastings[j]) ** 2
            noises[j] = calculate_noise_at_distance(dist)

        total_noise_result[i] = calculate_mixed_noise_level(noises)

    return total_noise_result


class NoiseTracker:
    def __init__(self):
        self.rows, self.cols = compute_grid_dimensions()
        self.drone_location_history = []
        self.noise_cells = build_cell_matrix()

    def track_drones(self, drones):
        self.drone_location_history.append([drone.location for drone in drones])

    def calculate_noise_cells(self):
        cell_northings = np.array([cell.centroid.northing for cell in self.noise_cells], dtype=np.float64)
        cell_eastings = np.array([cell.centroid.easting for cell in self.noise_cells], dtype=np.float64)

        with tqdm(total=len(self.drone_location_history), desc="Calculating Noise Matrix", unit="iteration") as pbar:
            for drone_locations in self.drone_location_history:
                drone_northings = np.array([loc.northing for loc in drone_locations], dtype=np.float64)
                drone_eastings = np.array([loc.easting for loc in drone_locations], dtype=np.float64)

                total_noise = calculate_cells_noise(
                    cell_northings,
                    cell_eastings,
                    drone_northings,
                    drone_eastings
                )

                for cell, noise in zip(self.noise_cells, total_noise):
                    cell.add_noise(noise)

                pbar.update(1)
