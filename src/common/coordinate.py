import math

from common.constants import M_2_LATITUDE, M_2_LONGITUDE


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


def calculate_distance(c1: Coordinate, c2: Coordinate):
    la_distance, lo_distance = c2 - c1

    la_distance_m = la_distance / M_2_LATITUDE
    lo_distance_m = lo_distance / M_2_LONGITUDE

    return math.sqrt(la_distance_m * la_distance_m +
                     lo_distance_m * lo_distance_m)
