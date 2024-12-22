import math

import geopandas as gpd
import numpy as np
import pandas as pd
from common.configuration import MAP_LEFT, MAP_RIGHT, MAP_TOP, MAP_BOTTOM, \
                                 NOISE_MATRIX_CELL_LENGTH, NOISE_MATRIX_CELL_WIDTH
from common.constants import M_2_LONGITUDE, M_2_LATITUDE
from common.coordinate import Coordinate, calculate_distance
from matrix.noise_math_utils import calculate_mixed_noise_level, calculate_noise_at_distance
from shapely.geometry import Point


class Cell:
    def __init__(self, latitude, longitude, row, column):
        self.row = row
        self.column = column
        self.centroid = Coordinate(latitude, longitude)
        self.total_noise = 0
        self.max_noise = 0
        self.population_density = 1

    def set_noise(self, noise):
        self.total_noise += noise
        self.max_noise = max(self.max_noise, noise)


class DensityMatrix:
    def __init__(self):
        self.cell_length_m = NOISE_MATRIX_CELL_LENGTH
        self.cell_width_m = NOISE_MATRIX_CELL_WIDTH

        self.cell_length_lo = self.cell_length_m * M_2_LONGITUDE
        self.cell_width_la = self.cell_width_m * M_2_LATITUDE
        self.rows = math.floor((MAP_TOP - MAP_BOTTOM) / self.cell_width_la)
        self.cols = math.floor((MAP_RIGHT - MAP_LEFT) / self.cell_length_lo)

        self.matrix = [[Cell(latitude=MAP_TOP - (i + 0.5) * self.cell_width_la,
                             longitude=MAP_LEFT + (j + 0.5) * self.cell_length_lo,
                             row=i, column=j)
                        for j in range(self.cols)] for i in range(self.rows)]

    def track_noise(self, drones):
        for row in self.matrix:
            for cell in row:
                noises = [
                    calculate_noise_at_distance(calculate_distance(cell.centroid, drone.location))
                    for drone in drones
                ]
                mixed_noise = calculate_mixed_noise_level(noises)
                cell.set_noise(mixed_noise)

    def get_cell(self, coordinate: Coordinate):
        lon = coordinate.longitude
        lat = coordinate.latitude

        if not self.is_valid(lon, lat):
            print(f"WARNING: No cell is found at (lon:{lon}, lat:{lat})")
            return None

        row = math.floor(abs(lat - MAP_TOP) / (self.cell_width_m * M_2_LATITUDE))
        col = math.floor(abs(lon - MAP_LEFT) / (self.cell_length_m * M_2_LONGITUDE))

        return self.matrix[row][col]

    def is_valid(self, longitude, latitude):
        if longitude >= MAP_RIGHT or longitude < MAP_LEFT:
            return False
        if latitude >= MAP_TOP or latitude < MAP_BOTTOM:
            return False
        return True

    def get_average_matrix(self, time_count):
        return np.array([[self.matrix[i][j].total_noise / time_count for j in range(self.cols)]
                         for i in range(self.rows)])
