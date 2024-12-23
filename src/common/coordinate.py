from dataclasses import dataclass
import math
from pyproj import Transformer

OSGB36_TO_WGS84 = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)


@dataclass
class Coordinate:
    northing: float  # y
    easting: float   # x

    def __eq__(self, other):
        if not isinstance(other, Coordinate):
            return NotImplemented
        return self.northing == other.northing and self.easting == other.easting

    def __sub__(self, other):
        return self.northing - other.northing, self.easting - other.easting

    def __str__(self):
        return f"[no={self.northing}, ea={self.easting}]"

    def convert_to_latlon(self):
        longitude, latitude = OSGB36_TO_WGS84.transform(self.easting, self.northing)
        return latitude, longitude


def calculate_distance(c1: Coordinate, c2: Coordinate):
    y_dist, x_dist = c2 - c1

    return math.hypot(y_dist, x_dist)
