from common.coordinate import Coordinate
from common.enum import NavigationType
from common.runtime_configs import get_simulation_config
from route_planner.landing_planner import AltitudePlanner
from route_planner.noise_based_planner import NoiseBasedPlanner
from route_planner.straight_line_planner import StraightLinePlanner


class PathPlanner:
    def __init__(self, dataset_path):
        navigator_type = get_simulation_config().navigator_type

        self.route_planner = self._init_route_planner(navigator_type, dataset_path)
        self.landing_planner = AltitudePlanner()

    @staticmethod
    def _init_route_planner(navigator_type, dataset_path):
        if navigator_type == NavigationType.STRAIGHT:
            return StraightLinePlanner()

        return NoiseBasedPlanner(dataset_path)

    def plan(self, start: Coordinate, end: Coordinate):
        route = self.route_planner.plan_route(start, end)

        padded_route = self.landing_planner.add_landing_sequence(route, start, end)
        altitudes = self.landing_planner.assign_altitudes(padded_route)

        return padded_route, altitudes
