from typing import List

import numpy as np
from common.coordinate import Coordinate, calculate_distance


def find_nearest_warehouse(warehouses: List[Coordinate], current_location: Coordinate) -> Coordinate:
    return warehouses[find_nearest_warehouse_location(warehouses, current_location)]


def find_nearest_warehouse_location(warehouses: List[Coordinate], current_location: Coordinate) -> int:
    distances = []

    for warehouse in warehouses:
        line_distance = calculate_distance(warehouse, current_location)

        distances.append(line_distance)

    return np.argmin(distances)


def get_difference(primary_list, exclusion_list):
    return [element for element in primary_list if element not in exclusion_list]
