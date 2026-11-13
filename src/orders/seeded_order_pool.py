"""Seed-labelled order pools: one set of destinations per seed, stocking derived from the same destinations."""
import random
from dataclasses import dataclass, replace
from itertools import accumulate
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

from common.coordinate import Coordinate
from common.enum import OrderDatasetType
from orders.destination_sampling import sample_destinations
from orders.order import Order

MAXIMUM_SAMPLING_ATTEMPTS = 10_000
COORDINATE_DECIMALS = 2
PARQUET_ENGINE = "fastparquet"


@dataclass(frozen=True)
class DemandZone:
    code: str
    polygon: BaseGeometry
    weight: float


def weight_zones_by_area(zones: list[DemandZone]) -> list[DemandZone]:
    return [replace(zone, weight=zone.polygon.area) for zone in zones]


def sample_point_in_polygon(polygon: BaseGeometry, random_generator, maximum_attempts: int) -> Point | None:
    """Uniform point by rejection sampling in the bounding box; None if every attempt misses."""
    minimum_x, minimum_y, maximum_x, maximum_y = polygon.bounds

    for _ in range(maximum_attempts):
        point = Point(random_generator.uniform(minimum_x, maximum_x), random_generator.uniform(minimum_y, maximum_y))
        if polygon.contains(point):
            return point

    return None


def make_zone_samplable(zone: DemandZone) -> DemandZone:
    polygon = zone.polygon if zone.polygon.is_valid else zone.polygon.buffer(0)
    shapely.prepare(polygon)
    return replace(zone, polygon=polygon)


def cumulative_weight_shares(zones: list[DemandZone]) -> list[float]:
    total_weight = sum(zone.weight for zone in zones)
    return list(accumulate(zone.weight / total_weight for zone in zones))


def generate_destinations(seed: int, number_of_orders: int, zones: list[DemandZone]) -> pd.DataFrame:
    """Destinations drawn zone by weight, then uniformly inside the zone, from a stream owned by the seed."""
    samplable_zones = [make_zone_samplable(zone) for zone in zones]
    sampled = sample_destinations(
        random.Random(f"destinations-{seed}"), number_of_orders, [zone.polygon for zone in samplable_zones],
        cumulative_weight_shares(samplable_zones), MAXIMUM_SAMPLING_ATTEMPTS,
    )

    return pd.DataFrame({
        "order_id": np.arange(1, number_of_orders + 1),
        "zone_code": [samplable_zones[zone_index].code for zone_index in sampled.zone_indices.tolist()],
        "end_northing": [round(northing, COORDINATE_DECIMALS) for northing in sampled.northings.tolist()],
        "end_easting": [round(easting, COORDINATE_DECIMALS) for easting in sampled.eastings.tolist()],
    })


def calculate_squared_distances_to_warehouses(destinations: pd.DataFrame, warehouses: list[Coordinate]) -> np.ndarray:
    """Matrix of squared distances with one row per destination and one column per warehouse."""
    warehouse_eastings = np.array([warehouse.easting for warehouse in warehouses])
    warehouse_northings = np.array([warehouse.northing for warehouse in warehouses])
    delta_eastings = destinations["end_easting"].to_numpy()[:, np.newaxis] - warehouse_eastings
    delta_northings = destinations["end_northing"].to_numpy()[:, np.newaxis] - warehouse_northings
    return delta_eastings ** 2 + delta_northings ** 2


def assign_warehouse_indices(
        destinations: pd.DataFrame, warehouses: list[Coordinate], stocking: OrderDatasetType, seed: int
) -> np.ndarray:
    match stocking:
        case OrderDatasetType.CLOSEST:
            return calculate_squared_distances_to_warehouses(destinations, warehouses).argmin(axis=1)
        case OrderDatasetType.FURTHEST:
            return calculate_squared_distances_to_warehouses(destinations, warehouses).argmax(axis=1)
        case OrderDatasetType.RANDOM:
            random_generator = random.Random(f"random-stocking-{seed}")
            return np.array([random_generator.randrange(len(warehouses)) for _ in range(len(destinations))])
        case _:
            raise ValueError(f"Unknown stocking: {stocking}")


def count_orders_per_warehouse(warehouse_indices: np.ndarray, warehouses: list[Coordinate]) -> dict[Coordinate, int]:
    counts = np.bincount(warehouse_indices, minlength=len(warehouses)).tolist()
    return {warehouse: count for warehouse, count in zip(warehouses, counts) if count > 0}


def build_orders_from_indices(
        destinations: pd.DataFrame, warehouses: list[Coordinate], warehouse_indices: np.ndarray
) -> list[Order]:
    """Order objects in pool order, each at its assigned warehouse."""
    return [
        Order(order_id=order_id, start_location=warehouses[warehouse_index], end_location=Coordinate(northing, easting))
        for order_id, warehouse_index, northing, easting in zip(
            destinations["order_id"].tolist(), warehouse_indices.tolist(),
            destinations["end_northing"].tolist(), destinations["end_easting"].tolist(),
        )
    ]


class PooledOrderQueue:
    """Orders of one warehouse in pool order; an Order object is built only when the order leaves the queue.

    Entries are (position in the pool, order), like the entries of the dispatcher's own queues.
    """

    def __init__(
            self, warehouse: Coordinate, pool_positions: np.ndarray, order_ids: np.ndarray,
            end_northings: np.ndarray, end_eastings: np.ndarray,
    ):
        self.warehouse = warehouse
        self._pool_positions = pool_positions
        self._order_ids = order_ids
        self._end_northings = end_northings
        self._end_eastings = end_eastings
        self._next_entry = 0

    def __len__(self):
        return len(self._pool_positions) - self._next_entry

    def __iter__(self):
        return (self._build_entry(entry) for entry in range(self._next_entry, len(self._pool_positions)))

    def popleft(self) -> tuple[int, Order]:
        if not self:
            raise IndexError("pop from an empty order queue")

        entry = self._build_entry(self._next_entry)
        self._next_entry += 1
        return entry

    def _build_entry(self, entry: int) -> tuple[int, Order]:
        end_location = Coordinate(self._end_northings[entry].item(), self._end_eastings[entry].item())
        order = Order(order_id=self._order_ids[entry].item(), start_location=self.warehouse, end_location=end_location)
        return self._pool_positions[entry].item(), order


def build_order_queues(
        destinations: pd.DataFrame, warehouses: list[Coordinate], warehouse_indices: np.ndarray
) -> dict[Coordinate, PooledOrderQueue]:
    """One queue per warehouse that has orders; together they hold the orders of build_orders_from_indices."""
    order_ids = destinations["order_id"].to_numpy()
    end_northings, end_eastings = destinations["end_northing"].to_numpy(), destinations["end_easting"].to_numpy()

    queues = {}
    for warehouse_index in np.unique(warehouse_indices).tolist():
        pool_positions = np.flatnonzero(warehouse_indices == warehouse_index)
        queues[warehouses[warehouse_index]] = PooledOrderQueue(
            warehouses[warehouse_index], pool_positions, order_ids[pool_positions],
            end_northings[pool_positions], end_eastings[pool_positions],
        )
    return queues


def build_orders(
        destinations: pd.DataFrame, warehouses: list[Coordinate], stocking: OrderDatasetType, seed: int
) -> list[Order]:
    warehouse_indices = assign_warehouse_indices(destinations, warehouses, stocking, seed)
    return build_orders_from_indices(destinations, warehouses, warehouse_indices)


def save_destination_pool(destinations: pd.DataFrame, pool_path: Path):
    destinations.to_parquet(pool_path, engine=PARQUET_ENGINE, index=False)


def load_destination_pool(pool_path: Path) -> pd.DataFrame:
    return pd.read_parquet(pool_path, engine=PARQUET_ENGINE)
