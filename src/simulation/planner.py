from __future__ import annotations

from common.coordinate import Coordinate
from common.enum import NavigationType
from common.runtime_configs import get_simulation_config
from route_planner.landing_planner import LandingPlanner
from route_planner.noise_based_planner import NoiseBasedPlanner
from route_planner.straight_line_planner import StraightLinePlanner
from simulation.planned_route_cache import PlannedRouteCache


class PathPlanner:
    def __init__(self, dataset_path, planned_route_cache: PlannedRouteCache | None = None):
        navigator_type = get_simulation_config().navigator_type

        self.route_planner = self._init_route_planner(navigator_type, dataset_path)
        self.landing_planner = LandingPlanner()
        self.planned_route_cache = planned_route_cache

    @staticmethod
    def _init_route_planner(navigator_type, dataset_path):
        if navigator_type == NavigationType.STRAIGHT:
            return StraightLinePlanner()

        return NoiseBasedPlanner(dataset_path)

    def plan(self, start: Coordinate, end: Coordinate):
        cached_planned_route = self._get_cached_planned_route(start, end)
        if cached_planned_route is not None:
            return cached_planned_route

        planned_route = self._build_planned_route(start, end)
        self._store_planned_route(start, end, planned_route)
        return planned_route

    def _get_cached_planned_route(self, start: Coordinate, end: Coordinate):
        if self.planned_route_cache is None:
            return None

        return self.planned_route_cache.get(start, end)

    def _build_planned_route(self, start: Coordinate, end: Coordinate):
        route = self.route_planner.plan_route(start, end)

        padded_route = self.landing_planner.add_landing_sequence(route, start, end)
        altitudes = self.landing_planner.assign_altitudes(padded_route)

        return padded_route, altitudes

    def _store_planned_route(self, start: Coordinate, end: Coordinate, planned_route):
        if self.planned_route_cache is None:
            return

        route, altitudes = planned_route
        self.planned_route_cache.store(start, end, route, altitudes)