"""Vectorised form of the one-order-at-a-time destination sampling; it reads the same random stream.

An order reads the stream as one uniform for its zone, then pairs of uniforms for candidate points in the
zone's bounding box until one lies inside the zone. Where an order starts therefore depends on every order
before it. The sampling is resolved for an order starting at every stream position at once, and the actual
orders are then found by following the chain of start positions from position 0.
"""
import random
from dataclasses import dataclass

import numpy as np
import shapely
from shapely.geometry.base import BaseGeometry

UNRESOLVED = -1
UNIFORMS_PER_ORDER_ESTIMATE = 6
MINIMUM_STREAM_EXTENSION = 1_000


@dataclass(frozen=True)
class SamplingZones:
    polygons: np.ndarray
    bounds: np.ndarray
    cumulative_shares: np.ndarray
    has_area: np.ndarray
    centroid_eastings: np.ndarray
    centroid_northings: np.ndarray


@dataclass(frozen=True)
class ResolvedStream:
    """Per stream position: the order that would start there, and where the order after it would start."""
    zone_indices: np.ndarray
    eastings: np.ndarray
    northings: np.ndarray
    next_positions: np.ndarray


@dataclass(frozen=True)
class SampledDestinations:
    zone_indices: np.ndarray
    eastings: np.ndarray
    northings: np.ndarray


def continue_python_random_stream(random_generator: random.Random) -> np.random.RandomState:
    """numpy generator whose uniforms are exactly those random_generator.random() would return next."""
    _, internal_state, _ = random_generator.getstate()
    stream = np.random.RandomState()
    stream.set_state(("MT19937", np.array(internal_state[:-1], dtype=np.uint32), internal_state[-1]))
    return stream


def build_sampling_zones(polygons: list[BaseGeometry], cumulative_shares: list[float]) -> SamplingZones:
    polygon_array = np.array(polygons, dtype=object)
    centroids = shapely.centroid(polygon_array)
    return SamplingZones(
        polygons=polygon_array,
        bounds=shapely.bounds(polygon_array),
        cumulative_shares=np.array(cumulative_shares),
        has_area=shapely.area(polygon_array) > 0,
        centroid_eastings=shapely.get_x(centroids),
        centroid_northings=shapely.get_y(centroids),
    )


def choose_zone_indices(uniforms: np.ndarray, cumulative_shares: np.ndarray) -> np.ndarray:
    return np.minimum(np.searchsorted(cumulative_shares, uniforms, side="left"), len(cumulative_shares) - 1)


def draw_candidate_points(
        positions: np.ndarray, attempt: int, uniforms: np.ndarray, zone_bounds: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Uniform points in the bounding boxes, from the pair of uniforms each order reads on this attempt."""
    first_uniform_positions = positions + 1 + 2 * attempt
    minimum_eastings, minimum_northings, maximum_eastings, maximum_northings = zone_bounds.T
    eastings = minimum_eastings + (maximum_eastings - minimum_eastings) * uniforms[first_uniform_positions]
    northings = minimum_northings + (maximum_northings - minimum_northings) * uniforms[first_uniform_positions + 1]
    return eastings, northings


def find_points_inside_their_zone(
        polygons: np.ndarray, zone_indices: np.ndarray, eastings: np.ndarray, northings: np.ndarray
) -> np.ndarray:
    """Tests all points of one zone in one call, which is many times faster than one call per point."""
    by_zone = np.argsort(zone_indices, kind="stable")
    zone_starts = np.flatnonzero(np.diff(zone_indices[by_zone])) + 1

    inside = np.zeros(len(zone_indices), dtype=bool)
    for points_of_zone in np.split(by_zone, zone_starts):
        if len(points_of_zone) > 0:
            polygon = polygons[zone_indices[points_of_zone[0]]]
            inside[points_of_zone] = shapely.contains_xy(polygon, eastings[points_of_zone], northings[points_of_zone])
    return inside


def resolve_stream(uniforms: np.ndarray, zones: SamplingZones, maximum_attempts: int) -> ResolvedStream:
    """Orders that run past the end of the stream stay unresolved; orders without a hit keep the centroid."""
    zone_indices = choose_zone_indices(uniforms, zones.cumulative_shares)
    eastings, northings = zones.centroid_eastings[zone_indices], zones.centroid_northings[zone_indices]
    next_positions = np.full(len(uniforms), UNRESOLVED, dtype=np.int64)

    positions = np.arange(len(uniforms))
    without_area = ~zones.has_area[zone_indices]
    next_positions[positions[without_area]] = positions[without_area] + 1

    pending = positions[~without_area]
    for attempt in range(maximum_attempts):
        pending = pending[pending + 2 + 2 * attempt < len(uniforms)]
        if len(pending) == 0:
            break

        candidate_eastings, candidate_northings = draw_candidate_points(
            pending, attempt, uniforms, zones.bounds[zone_indices[pending]]
        )
        inside = find_points_inside_their_zone(zones.polygons, zone_indices[pending], candidate_eastings, candidate_northings)
        accepted = pending[inside]
        eastings[accepted], northings[accepted] = candidate_eastings[inside], candidate_northings[inside]
        next_positions[accepted] = accepted + 3 + 2 * attempt
        pending = pending[~inside]

    next_positions[pending] = pending + 1 + 2 * maximum_attempts
    return ResolvedStream(zone_indices, eastings, northings, next_positions)


def follow_order_chain(next_positions: np.ndarray, number_of_orders: int) -> np.ndarray | None:
    """Stream positions at which the orders start; None if the stream ends before all of them are resolved."""
    order_positions = np.empty(number_of_orders, dtype=np.int64)
    position = 0
    for order in range(number_of_orders):
        if position >= len(next_positions) or next_positions[position] == UNRESOLVED:
            return None

        order_positions[order] = position
        position = next_positions[position]
    return order_positions


def sample_destinations(
        random_generator: random.Random, number_of_orders: int, polygons: list[BaseGeometry],
        cumulative_shares: list[float], maximum_attempts: int,
) -> SampledDestinations:
    """Zone and point of each order, as drawing them one at a time from random_generator would give."""
    zones = build_sampling_zones(polygons, cumulative_shares)
    stream = continue_python_random_stream(random_generator)
    stream_extension = number_of_orders * UNIFORMS_PER_ORDER_ESTIMATE + MINIMUM_STREAM_EXTENSION

    uniforms = np.empty(0)
    while True:
        uniforms = np.concatenate([uniforms, stream.random_sample(stream_extension)])
        resolved = resolve_stream(uniforms, zones, maximum_attempts)
        order_positions = follow_order_chain(resolved.next_positions, number_of_orders)
        if order_positions is not None:
            return SampledDestinations(
                resolved.zone_indices[order_positions], resolved.eastings[order_positions], resolved.northings[order_positions]
            )
