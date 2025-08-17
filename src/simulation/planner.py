from common.coordinate import Coordinate
from common.enum import NavigationType
from common.runtime_configs import runtime_simulation_config as sim_configs
from route_planner.landing_planner import AltitudePlanner
from route_planner.noise_based_planner import NoiseBasedPlanner
from route_planner.straight_line_planner import StraightLinePlanner


class PathPlanner:
    def __init__(self, dataset_path):
        self.route_planner = self._init_route_planner(dataset_path)
        self.landing_planner = AltitudePlanner()

    @staticmethod
    def _init_route_planner(dataset_path):
        if sim_configs.navigator_type == NavigationType.STRAIGHT:
            return StraightLinePlanner()

        return NoiseBasedPlanner(dataset_path)

    def plan(self, start: Coordinate, end: Coordinate):
        route = self.route_planner.plan_route(start, end)

        padded_route = self.landing_planner.add_landing_sequence(route, start, end)
        altitudes = self.landing_planner.assign_altitudes(padded_route)

        return padded_route, altitudes
