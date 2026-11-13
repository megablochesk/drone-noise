"""Run statistics on runs small enough to count by hand.

Counting rule (no terminal phases): a round trip of N intervals occupies 2 * (N + 1) + 1 time steps, and the
drone is recorded as airborne in all of them except the last, in which it is back at the warehouse.
"""
import numpy as np
import pytest

from common.coordinate import Coordinate
from common.enum import NoiseCalculation
from common.simulation_configs import SimulationConfig
from simulation.run_statistics import summarise_run
from tests.simulation.simulation_helpers import (
    WAREHOUSE,
    destination_east_of_warehouse,
    model_with_duration,
    run_small_simulation,
    write_order_dataset,
)

TWO_HOURS_S = 7_200
SECOND_WAREHOUSE = Coordinate(northing=165_727.01, easting=530_631.31)


def small_config(orders_path: str, number_of_orders: int, number_of_drones: int) -> SimulationConfig:
    return SimulationConfig(
        order_dataset_path=orders_path, orders_to_process=number_of_orders, number_of_drones=number_of_drones,
        print_model_stats=False, noise_calculation=NoiseCalculation.ENERGY_SUM, model=model_with_duration(TWO_HOURS_S),
    )


def test_single_drone_statistics(tmp_path):
    """9,000 m trips, N = 11: 25 steps per round trip, 24 of them airborne. 240 steps hold 9 round trips
    (216 airborne steps) and 15 airborne steps of the tenth: 231 * 30 s = 6,930 s, utilisation 6,930 / 7,200.
    The remaining 240 - 231 = 9 steps (the last step of each completed round trip) have no drone in the air."""
    orders_path = write_order_dataset(tmp_path / "orders.csv", [destination_east_of_warehouse(9_000.0)] * 40)
    statistics = summarise_run(run_small_simulation(small_config(orders_path, 40, 1)))

    assert statistics.delivered_orders == 9
    assert statistics.assigned_orders == 10
    assert statistics.simulated_duration_s == TWO_HOURS_S
    assert statistics.airborne_drone_seconds == 6_930
    assert statistics.utilisation == pytest.approx(6_930 / 7_200)
    assert statistics.time_steps_without_drones == 9
    assert statistics.pending_orders_by_warehouse == {WAREHOUSE: 30}
    np.testing.assert_allclose(statistics.trip_distances_m, [9_000.0] * 10)


def test_statistics_are_split_by_warehouse(tmp_path):
    """Two warehouses, one drone each, only the first has orders: it flies exactly as in the single-drone
    case (6,930 s, utilisation 0.9625) while the second stays idle (0 s), so the fleet utilisation halves."""
    orders_path = write_order_dataset(tmp_path / "orders.csv", [destination_east_of_warehouse(9_000.0)] * 40)
    simulator = run_small_simulation(small_config(orders_path, 40, 2), [WAREHOUSE, SECOND_WAREHOUSE])
    statistics = summarise_run(simulator)

    assert statistics.drones_by_warehouse == {WAREHOUSE: 1, SECOND_WAREHOUSE: 1}
    assert statistics.assigned_orders_by_warehouse == {WAREHOUSE: 10}
    assert statistics.airborne_drone_seconds_by_warehouse == {WAREHOUSE: 6_930, SECOND_WAREHOUSE: 0}
    assert statistics.utilisation_by_warehouse[WAREHOUSE] == pytest.approx(6_930 / 7_200)
    assert statistics.utilisation_by_warehouse[SECOND_WAREHOUSE] == 0
    assert statistics.utilisation == pytest.approx(6_930 / 14_400)


def test_run_that_exhausts_its_orders_reports_idle_steps_and_no_pending_orders(tmp_path):
    """Two 9,000 m orders, one drone: 2 * 25 = 50 steps of work, 48 of them airborne; the run then stops."""
    orders_path = write_order_dataset(tmp_path / "orders.csv", [destination_east_of_warehouse(9_000.0)] * 2)
    statistics = summarise_run(run_small_simulation(small_config(orders_path, 2, 1)))

    assert statistics.delivered_orders == 2
    assert statistics.pending_orders_by_warehouse == {}
    assert statistics.simulated_duration_s == 50 * 30
    assert statistics.airborne_drone_seconds == 48 * 30
    assert statistics.time_steps_without_drones == 2
