"""Stocking by distance works through the pool in blocks, so its memory does not grow with a full
destinations-by-warehouses distance table (73 MB per table for 650,000 orders and 14 warehouses)."""
import tracemalloc

import numpy as np
import pandas as pd
import pytest

from common.coordinate import Coordinate
from common.enum import OrderDatasetType
from orders import seeded_order_pool
from orders.seeded_order_pool import assign_warehouse_indices

NUMBER_OF_WAREHOUSES = 14
BYTES_PER_DISTANCE = 8
DISTANCE_STOCKINGS = [OrderDatasetType.CLOSEST, OrderDatasetType.FURTHEST]


def random_warehouses(generator: np.random.Generator) -> list[Coordinate]:
    return [
        Coordinate(northing=northing, easting=easting)
        for northing, easting in generator.uniform(0.0, 50_000.0, (NUMBER_OF_WAREHOUSES, 2)).tolist()
    ]


def random_destinations(generator: np.random.Generator, number_of_orders: int) -> pd.DataFrame:
    return pd.DataFrame({
        "order_id": np.arange(1, number_of_orders + 1),
        "zone_code": "ZONE",
        "end_northing": generator.uniform(0.0, 50_000.0, number_of_orders).round(2),
        "end_easting": generator.uniform(0.0, 50_000.0, number_of_orders).round(2),
    })


def brute_force_indices(destinations: pd.DataFrame, warehouses: list[Coordinate], choose) -> list[int]:
    indices = []
    for northing, easting in zip(destinations["end_northing"].tolist(), destinations["end_easting"].tolist()):
        squared_distances = [(w.easting - easting) ** 2 + (w.northing - northing) ** 2 for w in warehouses]
        indices.append(squared_distances.index(choose(squared_distances)))
    return indices


@pytest.mark.parametrize("stocking", DISTANCE_STOCKINGS)
def test_assignment_never_holds_a_full_distance_table(stocking):
    """Peak memory while assigning 400,000 orders stays below one 400,000 x 14 table of distances."""
    generator = np.random.default_rng(21)
    destinations, warehouses = random_destinations(generator, 400_000), random_warehouses(generator)
    full_table_bytes = len(destinations) * NUMBER_OF_WAREHOUSES * BYTES_PER_DISTANCE

    tracemalloc.start()
    assign_warehouse_indices(destinations, warehouses, stocking, seed=1)
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert peak_bytes < full_table_bytes


@pytest.mark.parametrize("stocking, choose", [(OrderDatasetType.CLOSEST, min), (OrderDatasetType.FURTHEST, max)])
@pytest.mark.parametrize("block_rows", [1, 7, 100, 5_000])
def test_assignment_does_not_depend_on_the_block_size(monkeypatch, stocking, choose, block_rows):
    """230 orders in blocks of 1, 7, 100 (last block shorter) and 5,000 (one block) against brute force."""
    monkeypatch.setattr(seeded_order_pool, "DISTANCE_BLOCK_ROWS", block_rows)
    generator = np.random.default_rng(22)
    destinations, warehouses = random_destinations(generator, 230), random_warehouses(generator)

    indices = assign_warehouse_indices(destinations, warehouses, stocking, seed=1)
    assert indices.tolist() == brute_force_indices(destinations, warehouses, choose)


@pytest.mark.parametrize("stocking", DISTANCE_STOCKINGS)
def test_first_of_two_equally_distant_warehouses_is_chosen(stocking):
    """Hand-built tie: warehouses 10 m east and 10 m west of the destination; the first listed one wins."""
    warehouses = [Coordinate(northing=0.0, easting=10.0), Coordinate(northing=0.0, easting=-10.0)]
    destinations = pd.DataFrame({"order_id": [1], "zone_code": ["ZONE"], "end_northing": [0.0], "end_easting": [0.0]})
    assert assign_warehouse_indices(destinations, warehouses, stocking, seed=1).tolist() == [0]


@pytest.mark.parametrize("stocking", DISTANCE_STOCKINGS)
def test_empty_pool_gives_no_indices(stocking):
    destinations = random_destinations(np.random.default_rng(23), 0)
    assert len(assign_warehouse_indices(destinations, random_warehouses(np.random.default_rng(24)), stocking, seed=1)) == 0
