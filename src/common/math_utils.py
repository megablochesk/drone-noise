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


def difference(list1, list2):
    return list(set(list1).difference(set(list2)))
