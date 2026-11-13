"""Rules that decide which warehouse each drone of the fleet calls home."""
import math
from typing import Iterable

from common.coordinate import Coordinate


def sort_warehouses_as_published(warehouses: Iterable[Coordinate]) -> list[Coordinate]:
    return sorted(set(warehouses), key=lambda warehouse: (warehouse.northing, warehouse.easting))


def allocate_fleet_equally(warehouses: Iterable[Coordinate], number_of_drones: int) -> list[Coordinate]:
    """Home warehouse of each drone, dealt round-robin over the sorted warehouses."""
    sorted_warehouses = sort_warehouses_as_published(warehouses)
    return [sorted_warehouses[drone % len(sorted_warehouses)] for drone in range(number_of_drones)]


def allocate_fleet_in_proportion_to_orders(
        order_counts: dict[Coordinate, int], number_of_drones: int
) -> list[Coordinate]:
    """Largest-remainder apportionment of the fleet to each warehouse's share of the orders."""
    sorted_warehouses = sort_warehouses_as_published(order_counts)
    total_orders = sum(order_counts.values())
    quotas = [order_counts[warehouse] * number_of_drones / total_orders for warehouse in sorted_warehouses]
    drones = [math.floor(quota) for quota in quotas]

    by_descending_remainder = sorted(
        range(len(quotas)), key=lambda index: quotas[index] - drones[index], reverse=True
    )
    for index in by_descending_remainder[:number_of_drones - sum(drones)]:
        drones[index] += 1

    return [warehouse for warehouse, count in zip(sorted_warehouses, drones) for _ in range(count)]
