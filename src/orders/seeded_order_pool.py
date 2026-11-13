"""Seed-labelled order pools: one set of destinations per seed, stocking derived from the same destinations."""
import random
from bisect import bisect_left
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


def sample_destination(zone: DemandZone, random_generator: random.Random) -> Point:
    if zone.polygon.area == 0:
        return zone.polygon.centroid

    point = sample_point_in_polygon(zone.polygon, random_generator, MAXIMUM_SAMPLING_ATTEMPTS)
    return zone.polygon.centroid if point is None else point


def cumulative_weight_shares(zones: list[DemandZone]) -> list[float]:
    total_weight = sum(zone.weight for zone in zones)
    return list(accumulate(zone.weight / total_weight for zone in zones))


def generate_destinations(seed: int, number_of_orders: int, zones: list[DemandZone]) -> pd.DataFrame:
    """Destinations drawn zone by weight, then uniformly inside the zone, from a stream owned by the seed."""
    random_generator = random.Random(f"destinations-{seed}")
    samplable_zones = [make_zone_samplable(zone) for zone in zones]
    cumulative_shares = cumulative_weight_shares(samplable_zones)
    last_zone_index = len(samplable_zones) - 1

    zone_codes, northings, eastings = [], [], []
    for _ in range(number_of_orders):
        zone_index = min(bisect_left(cumulative_shares, random_generator.random()), last_zone_index)
        point = sample_destination(samplable_zones[zone_index], random_generator)
        zone_codes.append(samplable_zones[zone_index].code)
        northings.append(round(point.y, COORDINATE_DECIMALS))
        eastings.append(round(point.x, COORDINATE_DECIMALS))

    return pd.DataFrame({
        "order_id": np.arange(1, number_of_orders + 1),
        "zone_code": zone_codes,
        "end_northing": northings,
        "end_easting": eastings,
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


def select_first_orders_per_warehouse(
        warehouse_indices: np.ndarray, maximum_orders_per_warehouse: dict[int, int]
) -> np.ndarray:
    """Mask of the orders that are among the first `limit` of their warehouse, in pool order."""
    indices = pd.Series(warehouse_indices)
    position_within_warehouse = indices.groupby(indices).cumcount()
    return (position_within_warehouse < indices.map(maximum_orders_per_warehouse)).to_numpy()


def build_orders_from_indices(
        destinations: pd.DataFrame, warehouses: list[Coordinate], warehouse_indices: np.ndarray,
        maximum_orders_per_warehouse: dict[int, int] | None,
) -> list[Order]:
    """Order objects in pool order; with limits, only the first few of each warehouse are built."""
    if maximum_orders_per_warehouse is not None:
        kept = select_first_orders_per_warehouse(warehouse_indices, maximum_orders_per_warehouse)
        destinations, warehouse_indices = destinations[kept], warehouse_indices[kept]

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
    return build_orders_from_indices(destinations, warehouses, warehouse_indices, maximum_orders_per_warehouse=None)


def save_destination_pool(destinations: pd.DataFrame, pool_path: Path):
    destinations.to_parquet(pool_path, engine=PARQUET_ENGINE, index=False)


def load_destination_pool(pool_path: Path) -> pd.DataFrame:
    return pd.read_parquet(pool_path, engine=PARQUET_ENGINE)
