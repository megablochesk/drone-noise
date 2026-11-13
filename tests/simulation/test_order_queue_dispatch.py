"""Equivalence of the two ways to feed orders: the eager order list and queues that build orders on dispatch."""
import random

import numpy as np
import pandas as pd
import pytest

from common.enum import NoiseCalculation
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from orders.seeded_order_pool import build_order_queues, build_orders_from_indices
from simulation.delivery_dispatcher import DeliveryDispatcher
from simulation.simulator import Simulator
from tests.simulation.simulation_helpers import (
    WAREHOUSE,
    destination_east_of_warehouse,
    model_with_duration,
    run_small_simulation,
)
from tests.simulation.test_delivery_dispatcher import (
    DESTINATION,
    WAREHOUSE_A,
    WAREHOUSE_B,
    WAREHOUSE_C,
    FleetStub,
    assigned_pairs,
    build_drones,
    pending_order_ids,
    release_random_drones,
)

TWO_HOURS_S = 7_200
UNUSED_DATASET_PATH = "unused.csv"


def run_simulation_from_queues(config: SimulationConfig, warehouse_locations, pending_orders_by_warehouse) -> Simulator:
    with use_simulation_config(config):
        simulator = Simulator(
            warehouse_locations=warehouse_locations, pending_orders_by_warehouse=pending_orders_by_warehouse
        )
        simulator.run()
    return simulator


def assigned_order_ids(dispatcher: DeliveryDispatcher) -> list[int]:
    return [order.order_id for order in dispatcher.assigned_orders]


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_dispatching_from_order_queues_matches_dispatching_from_the_order_list(seed):
    generator = random.Random(seed)
    warehouses = [WAREHOUSE_A, WAREHOUSE_B, WAREHOUSE_C]
    destinations = pd.DataFrame({
        "order_id": range(1, 401), "zone_code": "ZONE",
        "end_northing": DESTINATION.northing, "end_easting": DESTINATION.easting,
    })
    warehouse_indices = np.array(generator.choices(range(len(warehouses)), weights=[5, 2, 1], k=400))
    drone_warehouses = generator.choices(warehouses, k=25)

    list_dispatcher = DeliveryDispatcher(
        400, UNUSED_DATASET_PATH,
        orders=build_orders_from_indices(destinations, warehouses, warehouse_indices, maximum_orders_per_warehouse=None),
    )
    queue_dispatcher = DeliveryDispatcher(
        400, UNUSED_DATASET_PATH,
        pending_orders_by_warehouse=build_order_queues(destinations, warehouses, warehouse_indices),
    )
    list_fleet = FleetStub(free_drones=build_drones(drone_warehouses))
    queue_fleet = FleetStub(free_drones=build_drones(drone_warehouses))
    assert queue_dispatcher.pending_orders_number == list_dispatcher.pending_orders_number == 400

    for step in range(60):
        list_dispatcher.process_orders(list_fleet)
        queue_dispatcher.process_orders(queue_fleet)

        assert assigned_pairs(queue_fleet) == assigned_pairs(list_fleet)
        assert [drone.drone_id for drone in queue_fleet.free_drones] == [drone.drone_id for drone in list_fleet.free_drones]
        assert pending_order_ids(queue_dispatcher) == pending_order_ids(list_dispatcher)
        assert queue_dispatcher.pending_orders_per_warehouse() == list_dispatcher.pending_orders_per_warehouse()
        assert queue_dispatcher.pending_orders_number == list_dispatcher.pending_orders_number
        assert assigned_order_ids(queue_dispatcher) == assigned_order_ids(list_dispatcher)

        release_random_drones(list_fleet, random.Random(seed * 1000 + step))
        release_random_drones(queue_fleet, random.Random(seed * 1000 + step))


@pytest.mark.parametrize("drone_landing", [False, True])
def test_injected_order_queues_give_the_same_run_as_the_injected_order_list(tmp_path, drone_landing):
    generator = np.random.default_rng(11)
    warehouses = [WAREHOUSE, destination_east_of_warehouse(20_000.0)]
    destinations = pd.DataFrame({
        "order_id": np.arange(1, 501), "zone_code": "ZONE",
        "end_northing": (WAREHOUSE.northing + generator.uniform(-6_000.0, 6_000.0, 500)).round(2),
        "end_easting": (WAREHOUSE.easting + generator.uniform(0.0, 20_000.0, 500)).round(2),
    })
    warehouse_indices = generator.integers(0, len(warehouses), 500)
    config = SimulationConfig(
        order_dataset_path=str(tmp_path / "missing.csv"), number_of_drones=6, print_model_stats=False,
        drone_landing=drone_landing, noise_calculation=NoiseCalculation.ENERGY_SUM, model=model_with_duration(TWO_HOURS_S),
    )

    list_run = run_small_simulation(
        config, warehouse_locations=warehouses,
        orders=build_orders_from_indices(destinations, warehouses, warehouse_indices, maximum_orders_per_warehouse=None),
    )
    queue_run = run_simulation_from_queues(
        config, warehouses, build_order_queues(destinations, warehouses, warehouse_indices)
    )

    assert queue_run.delivered_orders_number == list_run.delivered_orders_number > 0
    assert assigned_order_ids(queue_run.dispatcher) == assigned_order_ids(list_run.dispatcher)
    assert queue_run.dispatcher.pending_orders_per_warehouse() == list_run.dispatcher.pending_orders_per_warehouse()
    assert queue_run.activity_log.drone_steps_by_warehouse == list_run.activity_log.drone_steps_by_warehouse
    pd.testing.assert_frame_equal(queue_run.noise_monitor.impact, list_run.noise_monitor.impact)
