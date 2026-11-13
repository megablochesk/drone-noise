import random
from dataclasses import replace

import pytest

from common.coordinate import Coordinate
from common.model_configs import model_config
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from route_planner.straight_line_planner import StraightLinePlanner
from tests.legacy_reference import load_legacy_module

LEGACY_PLANNER_MODULE = load_legacy_module("route_planner/straight_line_planner.py")
DEFAULT_STEP_DISTANCE_M = 27 * 30


def random_coordinate_pairs(number_of_pairs: int) -> list[tuple[Coordinate, Coordinate]]:
    generator = random.Random(20240601)
    pairs = []
    for _ in range(number_of_pairs):
        start = Coordinate(generator.uniform(156_000, 200_000), generator.uniform(504_000, 561_000))
        end = Coordinate(generator.uniform(156_000, 200_000), generator.uniform(504_000, 561_000))
        pairs.append((start, end))
    return pairs


def edge_case_pairs() -> list[tuple[Coordinate, Coordinate]]:
    origin = Coordinate(170_000.0, 530_000.0)
    return [
        (origin, origin),
        (origin, Coordinate(170_000.0, 530_000.0 + 0.5 * DEFAULT_STEP_DISTANCE_M)),
        (origin, Coordinate(170_000.0, 530_000.0 + 3 * DEFAULT_STEP_DISTANCE_M)),
        (origin, Coordinate(170_000.0 + 2.5 * DEFAULT_STEP_DISTANCE_M, 530_000.0)),
    ]


@pytest.mark.parametrize("start, end", random_coordinate_pairs(40) + edge_case_pairs())
def test_default_routes_match_the_published_implementation(start, end):
    """Characterisation: expected route comes from the planner source at the published baseline commit."""
    with use_simulation_config(SimulationConfig()):
        current_route = StraightLinePlanner().plan_route(start, end)
    assert current_route == LEGACY_PLANNER_MODULE.StraightLinePlanner().plan_route(start, end)


def test_injected_speed_and_time_step_set_the_waypoint_spacing():
    """Hand calculation: 30 m/s for 10 s is 300 m per step, so a 900 m leg has waypoints at 0, 300, 600, 900 m."""
    faster_model = replace(
        model_config,
        drone=replace(model_config.drone, speed_mps=30),
        time=replace(model_config.time, step_s=10),
    )
    start = Coordinate(170_000.0, 530_000.0)
    end = Coordinate(170_000.0, 530_900.0)
    with use_simulation_config(SimulationConfig(model=faster_model)):
        route = StraightLinePlanner().plan_route(start, end)
    assert [waypoint.easting - start.easting for waypoint in route] == pytest.approx([0.0, 300.0, 600.0, 900.0])
    assert all(waypoint.northing == start.northing for waypoint in route)
