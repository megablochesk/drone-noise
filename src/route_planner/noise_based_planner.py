import math

import numpy as np

from common.coordinate import Coordinate, calculate_distance
from common.model_configs import model_config
from common.runtime_configs import get_simulation_config
from noise.navigator import get_navigator
from route_planner.route_planner import RoutePlanner

PUBLISHED_TIME_STEP_S = model_config.time.step_s
PUBLISHED_SPEED_MPS = model_config.drone.speed_mps


class NoiseBasedPlanner(RoutePlanner):
    time_step_s = PUBLISHED_TIME_STEP_S
    speed_mps = PUBLISHED_SPEED_MPS

    def __init__(self, dataset_path, navigator=None):
        runtime_config = get_simulation_config()
        self.time_step_s = runtime_config.model.time.step_s
        self.speed_mps = runtime_config.model.drone.speed_mps
        self.navigator = navigator or get_navigator(
            mode=runtime_config.navigator_type,
            dataset_path=dataset_path,
            compute_on_miss=getattr(runtime_config, "compute_on_miss", False),
        )

    def plan_route(self, start: Coordinate, end: Coordinate) -> list[Coordinate]:
        if calculate_distance(start, end) == 0:
            return [start]

        route = self.navigator.get_optimal_route_coordinates(start, end)
        if route is None:
            return [start, end]

        sampled = to_coordinates(*resample_coordinates_by_time(*route, speed=self.speed_mps, dt=self.time_step_s))
        sampled[0] = start
        sampled[-1] = end
        return sampled


def to_coordinates(eastings: np.ndarray, northings: np.ndarray) -> list[Coordinate]:
    return [Coordinate(northing=northing, easting=easting) for northing, easting in zip(northings.tolist(), eastings.tolist())]


def resample_polyline_by_time(coords: list[Coordinate], speed: float, dt: float) -> list[Coordinate]:
    if len(coords) <= 2:
        return coords

    eastings = np.array([coordinate.easting for coordinate in coords])
    northings = np.array([coordinate.northing for coordinate in coords])
    return to_coordinates(*resample_coordinates_by_time(eastings, northings, speed, dt))


def resample_coordinates_by_time(
        eastings: np.ndarray, northings: np.ndarray, speed: float, dt: float
) -> tuple[np.ndarray, np.ndarray]:
    """Points every `speed * dt` metres along the polyline, plus its last point."""
    step_dist = speed * dt
    if len(eastings) <= 2 or step_dist <= 0:
        return eastings, northings

    cumulative_distances = calculate_cumulative_distances(eastings, northings)
    total = cumulative_distances[-1]
    if total <= 0:
        return eastings[[0, -1]], northings[[0, -1]]

    return resample_by_targets(eastings, northings, cumulative_distances, get_targets(total, step_dist))


def calculate_cumulative_distances(eastings: np.ndarray, northings: np.ndarray) -> np.ndarray:
    segment_lengths = [
        math.hypot(delta_northing, delta_easting)
        for delta_northing, delta_easting in zip(np.diff(northings).tolist(), np.diff(eastings).tolist())
    ]
    return np.concatenate([[0.0], np.cumsum(segment_lengths)])


def get_targets(total: float, step_dist: float) -> np.ndarray:
    if step_dist >= total:
        return np.array([0.0, total], dtype=float)
    t = np.arange(0.0, total, step_dist, dtype=float)
    if t.size == 0 or t[-1] != total:
        t = np.append(t, total)
    return t


def resample_by_targets(
        eastings: np.ndarray, northings: np.ndarray, cum: np.ndarray, targets: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Each target distance lies on the first segment that ends at or beyond it; zero-length segments give
    their start point."""
    segments = np.minimum(np.searchsorted(cum[1:], targets, side="left"), len(cum) - 2)
    segment_starts, segment_lengths = cum[segments], cum[segments + 1] - cum[segments]
    with np.errstate(divide="ignore", invalid="ignore"):
        shares = np.where(segment_lengths > 0.0, (targets - segment_starts) / segment_lengths, 0.0)

    sampled_eastings = eastings[segments] + (eastings[segments + 1] - eastings[segments]) * shares
    sampled_northings = northings[segments] + (northings[segments + 1] - northings[segments]) * shares
    return sampled_eastings, sampled_northings
