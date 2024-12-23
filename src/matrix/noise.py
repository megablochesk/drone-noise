import math
from dataclasses import dataclass, field
import numpy as np

from common.configuration import MAP_LEFT, MAP_RIGHT, MAP_TOP, MAP_BOTTOM, \
                                 NOISE_MATRIX_CELL_LENGTH, NOISE_MATRIX_CELL_WIDTH
from common.coordinate import Coordinate, calculate_distance
from matrix.noise_math_utils import calculate_mixed_noise_level, calculate_noise_at_distance


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


class DensityMatrix:
    def __init__(self):
        self.cell_length = NOISE_MATRIX_CELL_LENGTH
        self.cell_width = NOISE_MATRIX_CELL_WIDTH
        self.rows = math.floor((MAP_TOP - MAP_BOTTOM) / self.cell_width)
        self.cols = math.floor((MAP_RIGHT - MAP_LEFT) / self.cell_length)

        self.matrix = [
            [
                Cell(
                    row=r,
                    column=c,
                    centroid=Coordinate(
                        northing=MAP_TOP - (r + 0.5) * self.cell_width,
                        easting=MAP_LEFT + (c + 0.5) * self.cell_length,
                    ),
                )
                for c in range(self.cols)
            ]
            for r in range(self.rows)
        ]

    def track_noise(self, drones):
        for row in self.matrix:
            for cell in row:
                distances = [calculate_distance(cell.centroid, d.location) for d in drones]
                noises = [calculate_noise_at_distance(d) for d in distances]
                cell.add_noise(calculate_mixed_noise_level(noises))

    def get_cell(self, coordinate: Coordinate):
        if not self.is_valid(coordinate.easting, coordinate.northing):
            print(
                f"WARNING: No cell is found at "
                f"(easting:{coordinate.easting}, northing:{coordinate.northing})"
            )
            return None
        row = math.floor((MAP_TOP - coordinate.northing) / self.cell_width)
        col = math.floor((coordinate.easting - MAP_LEFT) / self.cell_length)
        return self.matrix[row][col]

    @staticmethod
    def is_valid(easting, northing):
        return (MAP_LEFT <= easting < MAP_RIGHT) and (MAP_BOTTOM <= northing < MAP_TOP)

    def get_average_matrix(self, time_count):
        return np.array([
            [cell.total_noise / time_count for cell in row]
            for row in self.matrix
        ])
