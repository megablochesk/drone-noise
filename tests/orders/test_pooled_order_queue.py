"""Per-warehouse order queues that build an Order object only when the order is dispatched.

Hand-built pool: warehouse indices 0, 1, 0, 0, 1 put orders 1, 3, 4 at the first warehouse and 2, 5 at the
second. A queue hands out (position in the pool, order), like the dispatcher's own queues.
"""
import numpy as np
import pandas as pd
import pytest

from common.coordinate import Coordinate
from orders import seeded_order_pool
from orders.order import Order
from orders.seeded_order_pool import build_order_queues, build_orders_from_indices

WAREHOUSES = [
    Coordinate(northing=500.0, easting=-2_000.0),
    Coordinate(northing=500.0, easting=3_000.0),
    Coordinate(northing=6_000.0, easting=7_000.0),
]
DESTINATIONS = pd.DataFrame({
    "order_id": [1, 2, 3, 4, 5],
    "zone_code": ["WEST"] * 5,
    "end_northing": [10.0, 20.0, 30.0, 40.0, 50.0],
    "end_easting": [11.0, 21.0, 31.0, 41.0, 51.0],
})
WAREHOUSE_INDICES = np.array([0, 1, 0, 0, 1])


def build_queues():
    return build_order_queues(DESTINATIONS, WAREHOUSES, WAREHOUSE_INDICES)


def test_each_warehouse_with_orders_has_one_queue():
    queues = build_queues()
    assert set(queues) == {WAREHOUSES[0], WAREHOUSES[1]}
    assert {warehouse: len(queue) for warehouse, queue in queues.items()} == {WAREHOUSES[0]: 3, WAREHOUSES[1]: 2}


def test_orders_leave_a_queue_in_pool_order_with_their_pool_position():
    queue = build_queues()[WAREHOUSES[0]]
    assert [queue.popleft() for _ in range(3)] == [
        (0, Order(order_id=1, start_location=WAREHOUSES[0], end_location=Coordinate(northing=10.0, easting=11.0))),
        (2, Order(order_id=3, start_location=WAREHOUSES[0], end_location=Coordinate(northing=30.0, easting=31.0))),
        (3, Order(order_id=4, start_location=WAREHOUSES[0], end_location=Coordinate(northing=40.0, easting=41.0))),
    ]


def test_queue_shrinks_as_orders_leave_and_is_falsy_when_empty():
    queue = build_queues()[WAREHOUSES[1]]
    assert len(queue) == 2 and queue
    queue.popleft()
    assert len(queue) == 1 and queue
    queue.popleft()
    assert len(queue) == 0 and not queue
    with pytest.raises(IndexError):
        queue.popleft()


def test_iterating_a_queue_lists_the_remaining_orders_without_removing_them():
    queue = build_queues()[WAREHOUSES[0]]
    queue.popleft()
    assert [(position, order.order_id) for position, order in queue] == [(2, 3), (3, 4)]
    assert len(queue) == 2


def test_order_objects_are_built_only_when_they_leave_the_queue(monkeypatch):
    built_order_ids = []

    def build_and_record(order_id, start_location, end_location):
        built_order_ids.append(order_id)
        return Order(order_id=order_id, start_location=start_location, end_location=end_location)

    monkeypatch.setattr(seeded_order_pool, "Order", build_and_record)
    queues = build_queues()
    assert built_order_ids == []

    queues[WAREHOUSES[1]].popleft()
    queues[WAREHOUSES[0]].popleft()
    assert built_order_ids == [2, 1]


def test_queues_hold_the_same_orders_as_the_eager_order_list():
    generator = np.random.default_rng(7)
    destinations = pd.DataFrame({
        "order_id": np.arange(1, 301),
        "zone_code": "WEST",
        "end_northing": generator.uniform(0.0, 9_000.0, 300).round(2),
        "end_easting": generator.uniform(0.0, 9_000.0, 300).round(2),
    })
    warehouse_indices = generator.integers(0, len(WAREHOUSES), 300)
    eager_orders = build_orders_from_indices(destinations, WAREHOUSES, warehouse_indices, maximum_orders_per_warehouse=None)

    queued = [entry for queue in build_order_queues(destinations, WAREHOUSES, warehouse_indices).values() for entry in queue]
    assert [order for _, order in sorted(queued, key=lambda entry: entry[0])] == eager_orders
    assert sorted(position for position, _ in queued) == list(range(300))
