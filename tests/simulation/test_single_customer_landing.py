"""Terminal phases with one landing per delivery.

Published behaviour: the drone descends at the customer, and the zero-length "delivering" leg is then padded
with a second full climb and descent, so a delivery costs six landing delays. With `land_once_at_customer`
the delivering leg is one time step on the ground and a delivery costs four: take-off and landing at the
warehouse and at the customer.

Hand calculation for a customer 9,000 m away at 27 m/s, 30 s steps and a 60 s landing delay (2 steps):
floor(9000 / 810) = 11 intervals, 12 cruise waypoints, plus 2 steps of climb and 2 of descent = 16 steps a leg.
"""
from dataclasses import replace

import pytest

from common.coordinate import Coordinate
from common.enum import NoiseCalculation, OrderDatasetType
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from experiments.revision.run_specification import RunSpecification, build_run_key, build_simulation_config
from orders.order import Order
from route_planner.landing_planner import LandingPlanner
from simulation.simulator import Simulator
from tests.simulation.simulation_helpers import WAREHOUSE, destination_east_of_warehouse, model_with_duration

TWO_HOURS_S = 7_200
CUSTOMER = destination_east_of_warehouse(9_000.0)
CRUISE_LEG_ALTITUDES_M = [0.0, 50.0] + [100.0] * 12 + [50.0, 0.0]
STORED_RUN_KEY = "af17b589ffe4e1c8"


def build_config(land_once_at_customer: bool, drone_landing: bool = True) -> SimulationConfig:
    return SimulationConfig(
        order_dataset_path="unused.csv", number_of_drones=1, print_model_stats=False, drone_landing=drone_landing,
        noise_calculation=NoiseCalculation.ENERGY_SUM, model=model_with_duration(TWO_HOURS_S),
        land_once_at_customer=land_once_at_customer,
    )


def build_orders(number_of_orders: int) -> list[Order]:
    return [Order(order_id=order_id, start_location=WAREHOUSE, end_location=CUSTOMER) for order_id in range(1, number_of_orders + 1)]


def trace_first_round_trip(config: SimulationConfig) -> list[tuple[Coordinate, float]]:
    """(location, altitude) of the drone at every time step until it is back and free."""
    with use_simulation_config(config):
        simulator = Simulator(warehouse_locations=[WAREHOUSE], orders=build_orders(1))
        trace = []
        while simulator.has_pending_deliveries:
            simulator.process_deliveries()
            trace.extend((drone.current_location, drone.current_altitude) for drone in simulator.fleet.delivering_drones)
            simulator.timer.advance()
    return trace


def count_deliveries(config: SimulationConfig) -> int:
    with use_simulation_config(config):
        simulator = Simulator(warehouse_locations=[WAREHOUSE], orders=build_orders(40))
        simulator.run()
    return simulator.delivered_orders_number


def test_published_delivery_lands_twice_at_the_customer():
    """Characterisation of the default: out (16 steps), a second climb and descent (0, 50, 100, 50, 0), back.
    The last step of the round trip, on the ground at the warehouse, frees the drone, so it is not traced."""
    altitudes = [altitude for _, altitude in trace_first_round_trip(build_config(land_once_at_customer=False))]
    assert altitudes == (CRUISE_LEG_ALTITUDES_M + [0.0, 50.0, 100.0, 50.0, 0.0] + CRUISE_LEG_ALTITUDES_M)[:-1]


def test_delivery_with_one_landing_spends_one_step_on_the_ground_at_the_customer():
    trace = trace_first_round_trip(build_config(land_once_at_customer=True))
    altitudes = [altitude for _, altitude in trace]
    assert altitudes == (CRUISE_LEG_ALTITUDES_M + [0.0] + CRUISE_LEG_ALTITUDES_M)[:-1]
    assert [location for location, _ in trace[14:19]] == [CUSTOMER] * 5
    assert trace[-1] == (WAREHOUSE, 50.0)


def test_one_landing_costs_four_landing_delays_and_two_landings_cost_six():
    """Round trip without terminal phases: 2 * 12 + 1 = 25 steps. Four landing delays add 8 steps (33), the
    published double landing adds 12 (37). Two hours are 240 steps: 9, 7 and 6 complete round trips."""
    assert count_deliveries(build_config(land_once_at_customer=False, drone_landing=False)) == 9
    assert count_deliveries(build_config(land_once_at_customer=True)) == 7
    assert count_deliveries(build_config(land_once_at_customer=False)) == 6


def test_the_switch_changes_nothing_without_terminal_phases():
    with_switch = trace_first_round_trip(build_config(land_once_at_customer=True, drone_landing=False))
    without_switch = trace_first_round_trip(build_config(land_once_at_customer=False, drone_landing=False))
    assert with_switch == without_switch
    assert {altitude for _, altitude in with_switch} == {100.0}


@pytest.mark.parametrize("land_once_at_customer, expected_plan", [
    (False, ([CUSTOMER] * 5, [0.0, 50.0, 100.0, 50.0, 0.0])),
    (True, ([CUSTOMER], [0.0])),
])
def test_zero_length_leg_of_the_landing_planner(land_once_at_customer, expected_plan):
    with use_simulation_config(build_config(land_once_at_customer)):
        planner = LandingPlanner()
        padded_route = planner.add_landing_sequence([CUSTOMER], CUSTOMER, CUSTOMER)
        assert (padded_route, planner.assign_altitudes(padded_route)) == expected_plan


def test_specification_keeps_the_published_landing_by_default():
    published = RunSpecification(
        stocking=OrderDatasetType.CLOSEST, number_of_drones=1250, terminal_phases=True, seed=1, pool_size=650_000
    )
    assert published.land_once_at_customer is False
    assert build_run_key(published) == STORED_RUN_KEY
    single_landing = replace(published, land_once_at_customer=True)
    assert build_run_key(single_landing) != STORED_RUN_KEY
    assert build_simulation_config(single_landing, "orders.csv", 10).land_once_at_customer is True
    assert build_simulation_config(published, "orders.csv", 10).land_once_at_customer is False
