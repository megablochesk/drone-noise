"""Small end-to-end runs whose delivery counts can be worked out by hand.

Stepping rule used in the hand calculations (straight line, no terminal phases): a leg of distance d has
N = floor(d / (speed * step)) intervals and N + 1 waypoints, one per time step; the drone spends one step at
the destination; a round trip therefore takes 2 * (N + 1) + 1 steps, and a delivery counts once the drone is
back at its warehouse.

These runs use the energy-sum noise path because it shares one cached grid; the delivery logic does not depend
on the noise path, and tests/noise/test_energy_noise_tracker.py runs the same simulator through both paths.
"""
import math
import random
from dataclasses import replace

import pytest

from common.enum import NoiseCalculation
from common.model_configs import model_config
from common.simulation_configs import SimulationConfig
from orders.order import Order
from tests.simulation.simulation_helpers import (
    WAREHOUSE,
    destination_east_of_warehouse,
    model_with_duration,
    run_small_simulation,
    write_order_dataset,
)

TWO_HOURS_S = 7_200
DESTINATION_DISTANCE_M = 9_000.0


def round_trip_steps(distance_m: float, speed_mps: float, time_step_s: float) -> int:
    return 2 * (math.floor(distance_m / (speed_mps * time_step_s)) + 1) + 1


def test_single_drone_delivery_count_with_published_parameters(tmp_path):
    """27 m/s, 30 s: N = floor(9000 / 810) = 11, round trip 25 steps; 240 steps hold 9 full round trips."""
    orders_path = write_order_dataset(tmp_path / "orders.csv", [destination_east_of_warehouse(9_000.0)] * 40)
    config = SimulationConfig(
        order_dataset_path=orders_path, orders_to_process=40, number_of_drones=1, print_model_stats=False,
        noise_calculation=NoiseCalculation.ENERGY_SUM,
        model=model_with_duration(TWO_HOURS_S),
    )
    assert run_small_simulation(config).delivered_orders_number == 9


def test_single_drone_delivery_count_with_injected_speed_and_time_step(tmp_path):
    """30 m/s, 10 s: N = floor(9000 / 300) = 30, round trip 63 steps; 720 steps hold 11 full round trips."""
    orders_path = write_order_dataset(tmp_path / "orders.csv", [destination_east_of_warehouse(9_000.0)] * 40)
    faster_model = replace(
        model_with_duration(TWO_HOURS_S),
        drone=replace(model_config.drone, speed_mps=30),
        time=replace(model_config.time, start_s=0, end_s=TWO_HOURS_S, step_s=10),
    )
    config = SimulationConfig(
        order_dataset_path=orders_path, orders_to_process=40, number_of_drones=1, print_model_stats=False,
        noise_calculation=NoiseCalculation.ENERGY_SUM,
        model=faster_model,
    )
    assert run_small_simulation(config).delivered_orders_number == 11


@pytest.mark.parametrize("number_of_drones", [1, 3])
def test_deliveries_never_exceed_the_fleet_throughput_bound(tmp_path, number_of_drones):
    """Invariant: deliveries <= fleet * duration / minimum round-trip time (shortest order, no waiting)."""
    generator = random.Random(5)
    distances_m = [generator.uniform(1_000.0, 12_000.0) for _ in range(200)]
    orders_path = write_order_dataset(
        tmp_path / "orders.csv", [destination_east_of_warehouse(distance_m) for distance_m in distances_m]
    )
    config = SimulationConfig(
        order_dataset_path=orders_path, orders_to_process=200, number_of_drones=number_of_drones,
        print_model_stats=False,
        noise_calculation=NoiseCalculation.ENERGY_SUM, model=model_with_duration(TWO_HOURS_S),
    )
    time_step_s = model_config.time.step_s
    minimum_round_trip_s = round_trip_steps(min(distances_m), model_config.drone.speed_mps, time_step_s) * time_step_s
    delivered = run_small_simulation(config).delivered_orders_number
    assert 0 < delivered <= number_of_drones * TWO_HOURS_S / minimum_round_trip_s


def test_injected_orders_replace_the_order_file(tmp_path):
    """Same 9,000 m scenario as the first test (9 round trips in two hours), but the orders are passed in as
    objects and the configured dataset path does not exist."""
    orders = [
        Order(order_id=order_id, start_location=WAREHOUSE, end_location=destination_east_of_warehouse(9_000.0))
        for order_id in range(1, 41)
    ]
    config = SimulationConfig(
        order_dataset_path=str(tmp_path / "missing.csv"), number_of_drones=1, print_model_stats=False,
        noise_calculation=NoiseCalculation.ENERGY_SUM, model=model_with_duration(TWO_HOURS_S),
    )
    assert run_small_simulation(config, orders=orders).delivered_orders_number == 9
