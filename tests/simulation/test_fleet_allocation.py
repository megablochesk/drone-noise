from collections import Counter

import pytest

from common.coordinate import Coordinate
from simulation.fleet_allocation import (
    allocate_fleet_equally,
    allocate_fleet_in_proportion_to_orders,
    sort_warehouses_as_published,
)

WAREHOUSE_A = Coordinate(northing=100.0, easting=900.0)
WAREHOUSE_B = Coordinate(northing=200.0, easting=100.0)
WAREHOUSE_C = Coordinate(northing=200.0, easting=500.0)


def test_warehouses_are_unique_and_sorted_by_northing_then_easting():
    """Published rule (`_load_active_warehouse_locations`): unique locations sorted by (northing, easting)."""
    unsorted = [WAREHOUSE_C, WAREHOUSE_A, WAREHOUSE_B, WAREHOUSE_C]
    assert sort_warehouses_as_published(unsorted) == [WAREHOUSE_A, WAREHOUSE_B, WAREHOUSE_C]


def test_equal_allocation_is_round_robin_over_the_sorted_warehouses():
    """Seven drones over three warehouses: 3, 2, 2, the remainder going to the first in sorted order."""
    homes = allocate_fleet_equally([WAREHOUSE_C, WAREHOUSE_B, WAREHOUSE_A], number_of_drones=7)
    assert homes == [WAREHOUSE_A, WAREHOUSE_B, WAREHOUSE_C, WAREHOUSE_A, WAREHOUSE_B, WAREHOUSE_C, WAREHOUSE_A]


def test_proportional_allocation_with_exact_quotas():
    """Order shares 50 %, 30 %, 20 % of ten drones: 5, 3, 2."""
    homes = allocate_fleet_in_proportion_to_orders({WAREHOUSE_A: 50, WAREHOUSE_B: 30, WAREHOUSE_C: 20}, 10)
    assert Counter(homes) == {WAREHOUSE_A: 5, WAREHOUSE_B: 3, WAREHOUSE_C: 2}


def test_proportional_allocation_gives_leftover_drones_to_the_largest_remainders():
    """Seven drones, shares 0.5, 0.3, 0.2: quotas 3.5, 2.1, 1.4 -> floors 3, 2, 1 and the seventh drone goes
    to the largest remainder (0.5): 4, 2, 1."""
    homes = allocate_fleet_in_proportion_to_orders({WAREHOUSE_A: 5, WAREHOUSE_B: 3, WAREHOUSE_C: 2}, 7)
    assert Counter(homes) == {WAREHOUSE_A: 4, WAREHOUSE_B: 2, WAREHOUSE_C: 1}


@pytest.mark.parametrize("number_of_drones", [1, 13, 100, 1250])
def test_fleet_split_sums_to_the_total_fleet(number_of_drones):
    """Invariant: no drone is created or lost by either allocation rule."""
    order_counts = {WAREHOUSE_A: 811, WAREHOUSE_B: 97, WAREHOUSE_C: 3_302}
    assert len(allocate_fleet_equally(list(order_counts), number_of_drones)) == number_of_drones
    assert len(allocate_fleet_in_proportion_to_orders(order_counts, number_of_drones)) == number_of_drones
