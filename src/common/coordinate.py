import math
from dataclasses import dataclass

from pyproj import Transformer

OSGB36_TO_WGS84 = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)


@dataclass
class Coordinate:
    northing: float  # y
    easting: float   # x

    def __str__(self):
        return f"[no={self.northing}, ea={self.easting}]"

    def convert_to_latlon(self):
        longitude, latitude = OSGB36_TO_WGS84.transform(self.easting, self.northing)
        return latitude, longitude


def calculate_distance(c1: Coordinate, c2: Coordinate):
    return math.hypot(c2.northing - c1.northing, c2.easting - c1.easting)


def calculate_squared_distance(c1: Coordinate, c2: Coordinate):
    return (c2.northing - c1.northing) ** 2 + (c2.easting - c1.easting) ** 2
