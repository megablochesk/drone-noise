import math
from pyproj import Transformer

OSGB36_TO_WGS84 = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)


class Coordinate:
    def __init__(self, northing: float, easting: float):
        self.northing = northing  # y
        self.easting = easting    # x
    
    def __eq__(self, other):
        return self.northing == other.northing and self.easting == other.easting
    
    def __sub__(self, other):
        return self.northing - other.northing, self.easting - other.easting
    
    def __str__(self):
        return f"[no={self.northing}, ea={self.easting}]"

    def convert_to_latlon(self):
        longitude, latitude = OSGB36_TO_WGS84.transform(self.easting, self.northing)

        return latitude, longitude


def calculate_distance(c1: Coordinate, c2: Coordinate):
    y_distance, x_distance = c2 - c1

    return math.sqrt(y_distance * y_distance +
                     x_distance * x_distance)
