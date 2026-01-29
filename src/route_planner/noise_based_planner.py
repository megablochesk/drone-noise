import numpy as np

from common.coordinate import Coordinate, calculate_distance
from common.model_configs import model_config
from common.runtime_configs import get_simulation_config
from noise.navigator import get_navigator
from route_planner.route_planner import RoutePlanner

MODEL_TIME_STEP = model_config.time.step_s
DRONE_SPEED = model_config.drone.speed_mps


class NoiseBasedPlanner(RoutePlanner):
    def __init__(self, dataset_path):
        runtime_config = get_simulation_config()
        self.navigator = get_navigator(
            mode=runtime_config.navigator_type,
            dataset_path=dataset_path,
            compute_on_miss=getattr(runtime_config, "compute_on_miss", False),
        )

    def plan_route(self, start: Coordinate, end: Coordinate) -> list[Coordinate]:
        if calculate_distance(start, end) == 0:
            return [start]

        path_nodes = self.navigator.get_optimal_route(start, end)
        if not path_nodes:
            return [start, end]

        coords = self.navigator.nodes_to_coordinates(path_nodes)
        sampled = resample_polyline_by_time(coords, speed=DRONE_SPEED, dt=MODEL_TIME_STEP)

        sampled[0] = start
        sampled[-1] = end
        return sampled


def resample_polyline_by_time(coords: list[Coordinate], speed: float, dt: float) -> list[Coordinate]:
    if len(coords) <= 2:
        return coords

    step_dist = speed * dt
    if step_dist <= 0:
        return coords

    cum = _cumulative_distances(coords)
    total = float(cum[-1])
    if total <= 0:
        return [coords[0], coords[-1]]

    targets = _targets(total, step_dist)
    return _resample_by_targets(coords, cum, targets)


def _cumulative_distances(coords: list[Coordinate]) -> np.ndarray:
    cum = np.zeros(len(coords), dtype=float)
    for i in range(1, len(coords)):
        cum[i] = cum[i - 1] + calculate_distance(coords[i - 1], coords[i])
    return cum


def _targets(total: float, step_dist: float) -> np.ndarray:
    if step_dist >= total:
        return np.array([0.0, total], dtype=float)
    t = np.arange(0.0, total, step_dist, dtype=float)
    if t.size == 0 or t[-1] != total:
        t = np.append(t, total)
    return t


def _resample_by_targets(coords: list[Coordinate], cum: np.ndarray, targets: np.ndarray) -> list[Coordinate]:
    out: list[Coordinate] = []
    j = 0
    n = len(coords)

    for d in targets:
        while j < n - 2 and cum[j + 1] < d:
            j += 1

        d0 = float(cum[j])
        d1 = float(cum[j + 1])
        seg = d1 - d0
        if seg <= 0.0:
            out.append(coords[j])
            continue

        t = (float(d) - d0) / seg
        a = coords[j]
        b = coords[j + 1]
        e = a.easting + (b.easting - a.easting) * t
        n_ = a.northing + (b.northing - a.northing) * t
        out.append(Coordinate(northing=n_, easting=e))

    return out
