from common.decorators import auto_str
from common.configuration import USE_POPULATION_DENSITY
from common.configuration import NOISE_CELL_LENGTH, NOISE_CELL_WIDTH
from common.configuration import MAP_LEFT, MAP_RIGHT, MAP_TOP, MAP_BOTTOM
from common.configuration import GEO_PATH, OLD_POPULATION_DENSITY_PATH
from common.constants import M_2_LONGITUDE, M_2_LATITUDE
from common.math_utils import calculate_mixed_noise_level, calculate_distance, calculate_noise_at_distance
from cityMap.citymap import Coordinate
import math
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache

@auto_str
class Cell:
    def __init__(self, latitude, longitude, row, col):
        self.row = row
        self.col = col
        self.centroid = Coordinate(latitude, longitude)
        self.total_noise = 0
        self.max_noise = 0
        self.population_density = 1

    def set_noise(self, noise):
        """
        Cell receives a mixed matrix and update its total and maximum matrix.
        
        :param noise: a mixed matrix
        :return:
        """
        self.total_noise += noise
        self.max_noise = max(self.max_noise, noise)


@auto_str
class DensityMatrix:
    def __init__(self):
        self.left = MAP_LEFT
        self.right = MAP_RIGHT
        self.top = MAP_TOP
        self.bottom = MAP_BOTTOM
        self.cell_length_m = NOISE_CELL_LENGTH
        self.cell_width_m = NOISE_CELL_WIDTH
        self.cell_length_lo = self.cell_length_m * M_2_LONGITUDE
        self.cell_width_la = self.cell_width_m * M_2_LATITUDE
        self.rows = math.floor((MAP_TOP - MAP_BOTTOM) / self.cell_width_la)
        self.cols = math.floor((MAP_RIGHT - MAP_LEFT) / self.cell_length_lo)
        self.matrix = [[Cell(latitude=self.top - (i + 1 / 2) * self.cell_width_la,
                             longitude=self.left + (j + 1 / 2) * self.cell_length_lo,
                             row=i, col=j)
                        for j in range(self.cols)] for i in range(self.rows)]
        if USE_POPULATION_DENSITY:
            self.load_pd()
        # TODO: how to use population density ...

    def load_pd(self):
        print("Loading population density data to the matrix...")
        geo = gpd.read_file(GEO_PATH)
        pd_data = pd.read_csv(OLD_POPULATION_DENSITY_PATH)
        # TODO: normalize population density first
        geo_pd_merged = geo.merge(pd_data, left_on="id2", right_on="tract")
        polys_geometry = geo_pd_merged.explode(index_parts=True, column='geometry')
        for i in range(self.rows):
            for j in range(self.cols):
                cell = self.matrix[i][j]
                centroid = cell.centroid
                p = Point(centroid.longitude, centroid.latitude)
                for _, line in polys_geometry.iterrows():
                    if line['geometry'].contains(p):
                        cell.population_density = line['Population_Density_in_2010']
                        break

    def track_noise(self, drones):
        """
        The matrix tracks all drones' matrix and record them to the matrix.

        :param drones: a list of delivering drones
        :return: none
        """
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
        if self.is_valid(lon, lat) is False:
            print(f"WARNING: No cell is found at (lon:{lon}, lat:{lat})")
            return None
        else:
            row = math.floor(abs(lat - self.top) / (self.cell_width_m * M_2_LATITUDE))
            col = math.floor(abs(lon - self.left) / (self.cell_length_m * M_2_LONGITUDE))
            return self.matrix[row][col]

    def is_valid(self, longitude, latitude):
        if longitude >= self.right or longitude < self.left:
            return False
        if latitude >= self.top or latitude < self.bottom:
            return False
        return True

    def get_maximum_matrix(self):
        return np.array([[self.matrix[i][j].max_noise for j in range(self.cols)]
                         for i in range(self.rows)])

    def get_pd_matrix(self):
        return np.array([[self.matrix[i][j].population_density for j in range(self.cols)]
                         for i in range(self.rows)])

    def calculate_std(self, time_count):
        return np.std(self.get_average_matrix(time_count))

    def get_average_matrix(self, time_count):
        return np.array([[self.matrix[i][j].total_noise / time_count for j in range(self.cols)]
                         for i in range(self.rows)])
