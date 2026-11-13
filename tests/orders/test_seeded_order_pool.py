"""Seeded order generation on hand-built zones and warehouses (no census data needed)."""
import math
import random

import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, box

from common.coordinate import Coordinate
from common.enum import OrderDatasetType
from orders.seeded_order_pool import (
    DemandZone,
    assign_warehouse_indices,
    build_orders,
    build_orders_from_indices,
    count_orders_per_warehouse,
    generate_destinations,
    load_destination_pool,
    save_destination_pool,
    weight_zones_by_area,
)

WEST_ZONE = DemandZone(code="WEST", polygon=box(0.0, 0.0, 1_000.0, 1_000.0), weight=3.0)
EAST_ZONE = DemandZone(code="EAST", polygon=box(5_000.0, 0.0, 9_000.0, 1_000.0), weight=1.0)
ZONES = [WEST_ZONE, EAST_ZONE]

WAREHOUSES = [
    Coordinate(northing=500.0, easting=-2_000.0),
    Coordinate(northing=500.0, easting=3_000.0),
    Coordinate(northing=6_000.0, easting=7_000.0),
    Coordinate(northing=-4_000.0, easting=12_000.0),
]


def squared_distance_m2(warehouse: Coordinate, easting: float, northing: float) -> float:
    return (warehouse.easting - easting) ** 2 + (warehouse.northing - northing) ** 2


def brute_force_warehouse_index(easting: float, northing: float, choose) -> int:
    distances = [math.sqrt(squared_distance_m2(warehouse, easting, northing)) for warehouse in WAREHOUSES]
    return distances.index(choose(distances))


def test_same_seed_gives_identical_destinations():
    """Invariant: generation is a pure function of the seed."""
    pd.testing.assert_frame_equal(generate_destinations(7, 500, ZONES), generate_destinations(7, 500, ZONES))


def test_different_seeds_give_different_destinations():
    """Invariant: independent streams; two 500-point samples of continuous coordinates cannot coincide."""
    first, second = generate_destinations(7, 500, ZONES), generate_destinations(8, 500, ZONES)
    assert not np.array_equal(first["end_easting"].to_numpy(), second["end_easting"].to_numpy())


def test_global_random_state_does_not_influence_the_pool():
    """Invariant: the generator owns its random stream (local random.Random)."""
    random.seed(1)
    first = generate_destinations(7, 200, ZONES)
    random.seed(2)
    pd.testing.assert_frame_equal(first, generate_destinations(7, 200, ZONES))


def test_destinations_lie_inside_a_zone_and_are_numbered_from_one():
    """Invariant: every destination is a point of some demand zone; ids are 1..n as in the published CSVs."""
    destinations = generate_destinations(3, 400, ZONES)
    assert destinations["order_id"].tolist() == list(range(1, 401))
    for easting, northing in zip(destinations["end_easting"], destinations["end_northing"]):
        point = Point(easting, northing)
        assert WEST_ZONE.polygon.covers(point) or EAST_ZONE.polygon.covers(point)


def test_zone_shares_follow_the_weights():
    """Weights 3:1 give an expected west share of 0.75; with n = 20,000 the standard error is
    sqrt(0.75 * 0.25 / 20000) = 0.0031, so 0.015 is almost five standard errors."""
    destinations = generate_destinations(11, 20_000, ZONES)
    west_share = (destinations["end_easting"] <= 1_000.0).mean()
    assert west_share == pytest.approx(0.75, abs=0.015)


def test_area_weighting_makes_demand_uniform_by_area():
    """The west zone is 1 km^2 and the east zone 4 km^2, so the expected west share is 1/5 = 0.2
    (standard error sqrt(0.2 * 0.8 / 20000) = 0.0028)."""
    area_zones = weight_zones_by_area(ZONES)
    assert [zone.weight for zone in area_zones] == [1_000_000.0, 4_000_000.0]
    destinations = generate_destinations(11, 20_000, area_zones)
    assert (destinations["end_easting"] <= 1_000.0).mean() == pytest.approx(0.2, abs=0.015)


@pytest.mark.parametrize("stocking, choose", [(OrderDatasetType.CLOSEST, min), (OrderDatasetType.FURTHEST, max)])
def test_closest_and_furthest_warehouses_agree_with_brute_force(stocking, choose):
    """Expected index: explicit loop over all warehouses with math.sqrt distances."""
    destinations = generate_destinations(5, 300, ZONES)
    indices = assign_warehouse_indices(destinations, WAREHOUSES, stocking, seed=5)
    expected = [
        brute_force_warehouse_index(easting, northing, choose)
        for easting, northing in zip(destinations["end_easting"], destinations["end_northing"])
    ]
    assert indices.tolist() == expected


def test_random_stocking_is_seeded_and_uses_every_warehouse():
    """Invariants: pure function of the seed; valid indices; with 2,000 draws over 4 warehouses each expected
    share is 0.25 with standard error sqrt(0.25 * 0.75 / 2000) = 0.0097, so 0.05 is five standard errors."""
    destinations = generate_destinations(5, 2_000, ZONES)
    first = assign_warehouse_indices(destinations, WAREHOUSES, OrderDatasetType.RANDOM, seed=5)
    again = assign_warehouse_indices(destinations, WAREHOUSES, OrderDatasetType.RANDOM, seed=5)
    other = assign_warehouse_indices(destinations, WAREHOUSES, OrderDatasetType.RANDOM, seed=6)

    np.testing.assert_array_equal(first, again)
    assert not np.array_equal(first, other)
    shares = np.bincount(first, minlength=len(WAREHOUSES)) / len(first)
    np.testing.assert_allclose(shares, 0.25, atol=0.05)


def test_the_three_stockings_share_their_destinations():
    """Invariant: stocking changes only the warehouse of an order, never its destination or id."""
    destinations = generate_destinations(9, 250, ZONES)
    orders_by_stocking = {
        stocking: build_orders(destinations, WAREHOUSES, stocking, seed=9) for stocking in OrderDatasetType
    }
    reference = orders_by_stocking[OrderDatasetType.CLOSEST]
    for orders in orders_by_stocking.values():
        assert [order.order_id for order in orders] == [order.order_id for order in reference]
        assert [order.end_location for order in orders] == [order.end_location for order in reference]
        assert all(order.start_location in WAREHOUSES for order in orders)
    closest_starts = [order.start_location for order in reference]
    furthest_starts = [order.start_location for order in orders_by_stocking[OrderDatasetType.FURTHEST]]
    assert closest_starts != furthest_starts


def test_destination_pool_survives_a_parquet_round_trip(tmp_path):
    """Invariant: saving and loading returns the same table."""
    destinations = generate_destinations(4, 300, ZONES)
    pool_path = tmp_path / "destinations_seed4.parquet"
    save_destination_pool(destinations, pool_path)
    pd.testing.assert_frame_equal(load_destination_pool(pool_path), destinations)


def test_orders_can_be_limited_to_the_first_few_per_warehouse():
    """Hand-built case: warehouse indices 0, 1, 0, 0, 1 with limits {0: 2, 1: 1} keep orders 1, 2 and 3
    (the third order of warehouse 0 and the second of warehouse 1 are dropped), in pool order."""
    destinations = pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5],
        "zone_code": ["WEST"] * 5,
        "end_northing": [10.0, 20.0, 30.0, 40.0, 50.0],
        "end_easting": [11.0, 21.0, 31.0, 41.0, 51.0],
    })
    orders = build_orders_from_indices(
        destinations, WAREHOUSES, np.array([0, 1, 0, 0, 1]), maximum_orders_per_warehouse={0: 2, 1: 1}
    )
    assert [order.order_id for order in orders] == [1, 2, 3]
    assert [order.start_location for order in orders] == [WAREHOUSES[0], WAREHOUSES[1], WAREHOUSES[0]]
    assert orders[2].end_location == Coordinate(northing=30.0, easting=31.0)


def test_orders_per_warehouse_are_counted_from_the_indices():
    """Hand-built case: indices 0, 1, 0, 0, 1 are three orders for warehouse 0 and two for warehouse 1."""
    counts = count_orders_per_warehouse(np.array([0, 1, 0, 0, 1]), WAREHOUSES)
    assert counts == {WAREHOUSES[0]: 3, WAREHOUSES[1]: 2}
