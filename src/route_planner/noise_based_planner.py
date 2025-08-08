import numpy as np

from common.configuration import NAVIGATOR_TYPE
from common.coordinate import calculate_distance
from common.model_configs import model_config
from noise.navigator import get_navigator
from route_planner.route_planner import RoutePlanner

MODEL_TIME_STEP = model_config.time.step_s
DRONE_SPEED = model_config.drone.speed_mps
NAVIGATION_GRID_CELL_SIZE = model_config.grid.nav_cell_m


class NoiseBasedPlanner(RoutePlanner):
    def __init__(self, dataset_path):
        self.navigator = get_navigator(NAVIGATOR_TYPE, dataset_path)

    def plan_route(self, start, end):
        if calculate_distance(start, end) == 0:
            return [start]

        path_nodes = self.navigator.get_optimal_route(start, end)
        route = self._sample_route_by_steps(path_nodes)

        route_coords = self.navigator.nodes_to_coordinates(route)

        if route_coords[0] != start:
            route_coords.insert(0, start)
        if route_coords[-1] != end:
            route_coords.append(end)

        return route_coords

    @staticmethod
    def _sample_route_by_steps(route):
        path_length = NAVIGATION_GRID_CELL_SIZE * (len(route) - 1)
        total_time = path_length / DRONE_SPEED
        steps = int(total_time // MODEL_TIME_STEP)

        if steps > 0 and len(route) > steps + 1:
            idx = np.linspace(0, len(route) - 1, steps + 1, dtype=int)
            route = [route[i] for i in idx]

        return route
