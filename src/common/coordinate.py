import math

from common.constants import M_2_LATITUDE, M_2_LONGITUDE


class Coordinate:
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude    # y
        self.longitude = longitude  # x
    
    def __eq__(self, other):
        return self.latitude == other.latitude and self.longitude == other.longitude
    
    def __sub__(self, other):
        return self.latitude - other.latitude, self.longitude - other.longitude
    
    def __str__(self):
        return f"[la={self.latitude}, lo={self.longitude}]"


def calculate_distance(c1: Coordinate, c2: Coordinate):
    la_distance, lo_distance = c2 - c1

    la_distance_m = la_distance / M_2_LATITUDE
    lo_distance_m = lo_distance / M_2_LONGITUDE

    return math.sqrt(la_distance_m * la_distance_m +
                     lo_distance_m * lo_distance_m)
