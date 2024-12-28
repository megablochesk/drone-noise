import math
from dataclasses import dataclass

from common.configuration import MAP_LEFT, MAP_RIGHT, MAP_TOP, MAP_BOTTOM, \
                                 NOISE_MATRIX_CELL_LENGTH, NOISE_MATRIX_CELL_WIDTH
from common.coordinate import Coordinate, calculate_squared_distance
from noise.noise_math_utils import calculate_mixed_noise_level, calculate_noise_at_distance
from tqdm import tqdm


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


class NoiseTracker:
    def __init__(self):
        self.rows = math.floor((MAP_TOP - MAP_BOTTOM) / NOISE_MATRIX_CELL_WIDTH)
        self.cols = math.floor((MAP_RIGHT - MAP_LEFT) / NOISE_MATRIX_CELL_LENGTH)

        self.drone_location_history = []
        self.noise_matrix = [
            [
                Cell(
                    row=r,
                    column=c,
                    centroid=Coordinate(
                        northing=MAP_TOP - (r + 0.5) * NOISE_MATRIX_CELL_WIDTH,
                        easting=MAP_LEFT + (c + 0.5) * NOISE_MATRIX_CELL_LENGTH,
                    ),
                )
                for c in range(self.cols)
            ]
            for r in range(self.rows)
        ]

    def track_drones(self, drones):
        drone_locations = [drone.location for drone in drones]
        self.drone_location_history.append(drone_locations)

    def calculate_noise_in_cell(self, drone_locations):
        for row in self.noise_matrix:
            for cell in row:
                squared_distances = [calculate_squared_distance(cell.centroid, drone_location)
                                     for drone_location in drone_locations]

                noises = [calculate_noise_at_distance(distance) for distance in squared_distances]

                cell.add_noise(calculate_mixed_noise_level(noises))

    def calculate_noise_matrix(self):
        with tqdm(total=len(self.drone_location_history), desc="Calculating Noise Matrix", unit="iteration") as process_bar:
            for drone_locations in self.drone_location_history:
                self.calculate_noise_in_cell(drone_locations)
                process_bar.update(1)
