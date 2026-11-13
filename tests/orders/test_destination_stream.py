"""The destination pool of a seed is a fixed dataset: any faster generator must reproduce it exactly.

Two independent references pin the pools down:
- recorded pools (tests/orders/data), written by the one-order-at-a-time generator at commit da275b6;
- `generate_destinations_one_at_a_time` below, a plain restatement of the sampling rule: draw the zone, then
  rejection-sample a point in the zone's bounding box, all from random.Random(f"destinations-{seed}").

The zones cover every branch: no rejection (square), rejection (triangle, ring with a hole), a zone without
area (point: its centroid is used and no point is drawn), and an invalid polygon that is repaired first.
"""
import random
from bisect import bisect_left
from pathlib import Path

import pandas as pd
import pytest
from shapely.geometry import Point, Polygon, box

from orders import seeded_order_pool
from orders.seeded_order_pool import (
    COORDINATE_DECIMALS,
    DemandZone,
    cumulative_weight_shares,
    generate_destinations,
    make_zone_samplable,
)

RECORDED_POOLS_DIRECTORY = Path(__file__).parent / "data"
ZONES = [
    DemandZone(code="SQUARE", polygon=box(0.0, 0.0, 1_000.0, 1_000.0), weight=3.0),
    DemandZone(code="TRIANGLE", polygon=Polygon([(2_000.0, 0.0), (4_000.0, 0.0), (2_000.0, 3_000.0)]), weight=2.0),
    DemandZone(
        code="RING",
        polygon=Polygon(
            [(5_000.0, 0.0), (7_000.0, 0.0), (7_000.0, 2_000.0), (5_000.0, 2_000.0)],
            holes=[[(5_500.0, 500.0), (6_500.0, 500.0), (6_500.0, 1_500.0), (5_500.0, 1_500.0)]],
        ),
        weight=2.0,
    ),
    DemandZone(code="POINT", polygon=Point(9_000.0, 500.0), weight=0.5),
    DemandZone(
        code="BOWTIE",
        polygon=Polygon([(10_000.0, 0.0), (12_000.0, 2_000.0), (12_000.0, 0.0), (10_000.0, 2_000.0)]),
        weight=1.0,
    ),
]
# A sliver filling 1 % of its bounding box: with two attempts allowed, most orders fall back to the centroid.
SLIVER_ZONES = [
    DemandZone(code="SLIVER", polygon=Polygon([(0.0, 0.0), (1_000.0, 980.0), (1_000.0, 1_000.0)]), weight=1.0),
    DemandZone(code="SQUARE", polygon=box(2_000.0, 0.0, 3_000.0, 1_000.0), weight=1.0),
]
TWO_ATTEMPTS = 2


def read_recorded_pool(file_name: str) -> pd.DataFrame:
    return pd.read_csv(RECORDED_POOLS_DIRECTORY / file_name, float_precision="round_trip")


def sample_point_one_at_a_time(zone: DemandZone, random_generator: random.Random, maximum_attempts: int) -> Point:
    if zone.polygon.area == 0:
        return zone.polygon.centroid

    minimum_x, minimum_y, maximum_x, maximum_y = zone.polygon.bounds
    for _ in range(maximum_attempts):
        point = Point(random_generator.uniform(minimum_x, maximum_x), random_generator.uniform(minimum_y, maximum_y))
        if zone.polygon.contains(point):
            return point

    return zone.polygon.centroid


def generate_destinations_one_at_a_time(
        seed: int, number_of_orders: int, zones: list[DemandZone], maximum_attempts: int
) -> pd.DataFrame:
    random_generator = random.Random(f"destinations-{seed}")
    samplable_zones = [make_zone_samplable(zone) for zone in zones]
    cumulative_shares = cumulative_weight_shares(samplable_zones)

    rows = []
    for order_id in range(1, number_of_orders + 1):
        zone = samplable_zones[min(bisect_left(cumulative_shares, random_generator.random()), len(zones) - 1)]
        point = sample_point_one_at_a_time(zone, random_generator, maximum_attempts)
        rows.append((order_id, zone.code, round(point.y, COORDINATE_DECIMALS), round(point.x, COORDINATE_DECIMALS)))
    return pd.DataFrame(rows, columns=["order_id", "zone_code", "end_northing", "end_easting"])


def test_pool_of_seed_seven_is_the_recorded_pool():
    recorded = read_recorded_pool("destinations_seed7_n1500.csv")
    pd.testing.assert_frame_equal(generate_destinations(7, 1_500, ZONES), recorded, check_exact=True)
    assert set(recorded["zone_code"]) == {"SQUARE", "TRIANGLE", "RING", "POINT", "BOWTIE"}


def test_pool_with_exhausted_attempts_is_the_recorded_pool(monkeypatch):
    monkeypatch.setattr(seeded_order_pool, "MAXIMUM_SAMPLING_ATTEMPTS", TWO_ATTEMPTS)
    recorded = read_recorded_pool("destinations_seed3_n400_two_attempts.csv")
    pd.testing.assert_frame_equal(generate_destinations(3, 400, SLIVER_ZONES), recorded, check_exact=True)

    sliver_centroid = SLIVER_ZONES[0].polygon.centroid
    at_centroid = recorded[
        (recorded["end_easting"] == round(sliver_centroid.x, COORDINATE_DECIMALS))
        & (recorded["end_northing"] == round(sliver_centroid.y, COORDINATE_DECIMALS))
    ]
    assert len(at_centroid) > 100


@pytest.mark.parametrize("seed, number_of_orders", [(1, 1), (2, 37), (3, 800), (11, 2_500)])
def test_pool_follows_the_one_at_a_time_sampling_rule(seed, number_of_orders):
    pd.testing.assert_frame_equal(
        generate_destinations(seed, number_of_orders, ZONES),
        generate_destinations_one_at_a_time(seed, number_of_orders, ZONES, seeded_order_pool.MAXIMUM_SAMPLING_ATTEMPTS),
        check_exact=True,
    )


def test_pool_with_exhausted_attempts_follows_the_one_at_a_time_sampling_rule(monkeypatch):
    monkeypatch.setattr(seeded_order_pool, "MAXIMUM_SAMPLING_ATTEMPTS", TWO_ATTEMPTS)
    pd.testing.assert_frame_equal(
        generate_destinations(5, 600, SLIVER_ZONES),
        generate_destinations_one_at_a_time(5, 600, SLIVER_ZONES, TWO_ATTEMPTS),
        check_exact=True,
    )


def test_longer_pool_starts_with_the_shorter_pool_of_the_same_seed():
    """Invariant of a single stream: asking for more orders appends to the pool and never changes its start."""
    pd.testing.assert_frame_equal(
        generate_destinations(4, 2_000, ZONES).head(500), generate_destinations(4, 500, ZONES), check_exact=True
    )
