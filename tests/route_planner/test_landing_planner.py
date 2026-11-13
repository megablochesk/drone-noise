from dataclasses import replace

import pytest

from common.coordinate import Coordinate
from common.model_configs import model_config
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from route_planner.landing_planner import LandingPlanner
from tests.legacy_reference import load_legacy_module

LEGACY_LANDING_MODULE = load_legacy_module("route_planner/landing_planner.py")

START = Coordinate(170_000.0, 530_000.0)
END = Coordinate(171_000.0, 532_000.0)


def straight_route(number_of_waypoints: int) -> list[Coordinate]:
    if number_of_waypoints == 1:
        return [START]
    fractions = [index / (number_of_waypoints - 1) for index in range(number_of_waypoints)]
    return [
        Coordinate(START.northing + fraction * (END.northing - START.northing),
                   START.easting + fraction * (END.easting - START.easting))
        for fraction in fractions
    ]


def plan_with(planner, number_of_waypoints: int):
    padded_route = planner.add_landing_sequence(straight_route(number_of_waypoints), START, END)
    return padded_route, planner.assign_altitudes(padded_route)


@pytest.mark.parametrize("terminal_phases", [False, True])
@pytest.mark.parametrize("number_of_waypoints", [1, 2, 3, 12])
def test_default_landing_plan_matches_the_published_implementation(terminal_phases, number_of_waypoints):
    """Characterisation: expected plan comes from the planner source at the published baseline commit."""
    with use_simulation_config(SimulationConfig(drone_landing=terminal_phases)):
        current_plan = plan_with(LandingPlanner(), number_of_waypoints)
        legacy_plan = plan_with(LEGACY_LANDING_MODULE.LandingPlanner(), number_of_waypoints)
    assert current_plan == legacy_plan


@pytest.mark.parametrize(
    "landing_delay_s, time_step_s, cruise_altitude_m, expected_climb_altitudes_m",
    [
        (60, 30, 100.0, [0.0, 50.0]),
        (120, 30, 100.0, [0.0, 25.0, 50.0, 75.0]),
        (30, 30, 100.0, [0.0]),
        (60, 10, 120.0, [0.0, 20.0, 40.0, 60.0, 80.0, 100.0]),
    ],
)
def test_injected_landing_delay_sets_the_altitude_ladder(
    landing_delay_s, time_step_s, cruise_altitude_m, expected_climb_altitudes_m
):
    """Hand calculation: ceil(delay / step) rungs, evenly spaced from the ground up to (not including) cruise."""
    injected_model = replace(
        model_config,
        drone=replace(model_config.drone, landing_delay_s=landing_delay_s, flight_altitude_m=cruise_altitude_m),
        time=replace(model_config.time, step_s=time_step_s),
    )
    with use_simulation_config(SimulationConfig(drone_landing=True, model=injected_model)):
        _, altitudes = plan_with(LandingPlanner(), number_of_waypoints=3)
    expected_altitudes = (
        expected_climb_altitudes_m + [cruise_altitude_m] * 3 + list(reversed(expected_climb_altitudes_m))
    )
    assert altitudes == pytest.approx(expected_altitudes)
