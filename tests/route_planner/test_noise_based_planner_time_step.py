"""Noise-aware routes must be sampled at the time step and speed of the run, as straight routes are."""
import math
from dataclasses import replace

import numpy as np

from common.coordinate import Coordinate
from common.model_configs import model_config
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from route_planner.noise_based_planner import NoiseBasedPlanner
from tests.route_planner.test_noise_based_planner_characterisation import GRID_SOUTH_M, GRID_WEST_M, build_planners

FINE_TIME_STEP_S = 10
SLOW_SPEED_MPS = 20


def configure_run(time_step_s: int, speed_mps: int) -> SimulationConfig:
    model = replace(
        model_config, time=replace(model_config.time, step_s=time_step_s), drone=replace(model_config.drone, speed_mps=speed_mps)
    )
    return SimulationConfig(model=model)


def test_route_points_are_one_time_step_of_flight_apart():
    """A route of length L sampled every 20 m/s x 10 s = 200 m has ceil(L / 200) + 1 points, none further apart."""
    _, _, navigator = build_planners(seed=1)
    warehouse = Coordinate(northing=GRID_SOUTH_M + 2_000.0, easting=GRID_WEST_M + 2_500.0)
    customer = Coordinate(northing=GRID_SOUTH_M + 3_650.0, easting=GRID_WEST_M + 4_420.0)
    eastings, northings = navigator.get_optimal_route_coordinates(warehouse, customer)
    route_length_m = np.hypot(np.diff(eastings), np.diff(northings)).sum()

    with use_simulation_config(configure_run(FINE_TIME_STEP_S, SLOW_SPEED_MPS)):
        route = NoiseBasedPlanner(dataset_path=None, navigator=navigator).plan_route(warehouse, customer)

    spacing_m = SLOW_SPEED_MPS * FINE_TIME_STEP_S
    gaps_m = [math.hypot(a.northing - b.northing, a.easting - b.easting) for a, b in zip(route[1:-1], route[2:-1])]
    assert len(route) == math.ceil(route_length_m / spacing_m) + 1
    assert max(gaps_m) <= spacing_m + 1e-6


class OnePointNavigator:
    """A navigator whose grid has both ends in one cell."""

    def get_optimal_route_coordinates(self, start, end):
        return None


def test_a_delivery_within_one_navigation_cell_is_flown_straight():
    """Without a grid route the drone still has to reach the customer: the route is start, end."""
    start = Coordinate(northing=GRID_SOUTH_M, easting=GRID_WEST_M)
    end = Coordinate(northing=GRID_SOUTH_M + 20.0, easting=GRID_WEST_M + 28.0)

    with use_simulation_config(configure_run(FINE_TIME_STEP_S, SLOW_SPEED_MPS)):
        route = NoiseBasedPlanner(dataset_path=None, navigator=OnePointNavigator()).plan_route(start, end)

    assert route == [start, end]
