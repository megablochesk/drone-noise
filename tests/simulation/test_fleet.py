"""Characterisation of the fleet bookkeeping against the fleet source at the published baseline commit.

The order of the three drone lists matters: free drones are dispatched from the end of their list, and the
delivering list fixes the order in which positions reach the noise stage.
"""
import random

import pytest

from common.coordinate import Coordinate
from common.enum import NoiseCalculation
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from orders.order import Order
from simulation.delivery_dispatcher import DeliveryDispatcher
from simulation.fleet import Fleet
from tests.legacy_reference import load_legacy_fleet

LEGACY_FLEET_MODULE = load_legacy_fleet()

WAREHOUSES = [
    Coordinate(northing=180_000.0, easting=530_000.0),
    Coordinate(northing=185_000.0, easting=535_000.0),
    Coordinate(northing=175_000.0, easting=540_000.0),
]
NUMBER_OF_DRONES = 30
NUMBER_OF_ORDERS = 600
NUMBER_OF_STEPS = 150
UNUSED_DATASET_PATH = "unused.csv"


def build_orders(seed: int) -> list[Order]:
    """Destinations 0.5 to 6 km from their warehouse, so drones complete many round trips of unequal length."""
    generator = random.Random(seed)
    orders = []
    for order_id in range(1, NUMBER_OF_ORDERS + 1):
        warehouse = generator.choices(WAREHOUSES, weights=[5, 2, 1])[0]
        destination = Coordinate(
            northing=warehouse.northing + generator.uniform(-4_000.0, 4_000.0),
            easting=warehouse.easting + generator.uniform(500.0, 4_500.0),
        )
        orders.append(Order(order_id=order_id, start_location=warehouse, end_location=destination))
    return orders


def advance_one_step(fleet, dispatcher: DeliveryDispatcher):
    dispatcher.process_orders(fleet)
    fleet.plan_drones_path()
    fleet.update_drones()


def describe_fleet(fleet) -> dict:
    return {
        "free": [drone.drone_id for drone in fleet.free_drones],
        "waiting_planning": [drone.drone_id for drone in fleet.waiting_planning_drones],
        "delivering": [
            (drone.drone_id, drone.status, drone.current_location, drone.current_altitude, drone.order.order_id)
            for drone in fleet.delivering_drones
        ],
    }


@pytest.mark.parametrize("drone_landing", [False, True])
@pytest.mark.parametrize("seed", [1, 2])
def test_drone_lists_match_the_published_fleet_at_every_step(drone_landing, seed):
    config = SimulationConfig(
        number_of_drones=NUMBER_OF_DRONES, drone_landing=drone_landing, print_model_stats=False,
        noise_calculation=NoiseCalculation.ENERGY_SUM,
    )
    with use_simulation_config(config):
        current_fleet = Fleet(NUMBER_OF_DRONES, UNUSED_DATASET_PATH, WAREHOUSES)
        legacy_fleet = LEGACY_FLEET_MODULE.Fleet(NUMBER_OF_DRONES, UNUSED_DATASET_PATH, WAREHOUSES)
        current_dispatcher = DeliveryDispatcher(NUMBER_OF_ORDERS, UNUSED_DATASET_PATH, orders=build_orders(seed))
        legacy_dispatcher = DeliveryDispatcher(NUMBER_OF_ORDERS, UNUSED_DATASET_PATH, orders=build_orders(seed))

        completed_round_trips = 0
        for _ in range(NUMBER_OF_STEPS):
            advance_one_step(current_fleet, current_dispatcher)
            advance_one_step(legacy_fleet, legacy_dispatcher)
            assert describe_fleet(current_fleet) == describe_fleet(legacy_fleet)
            completed_round_trips = len(current_dispatcher.assigned_orders) - len(current_fleet.delivering_drones)

    assert completed_round_trips > 3 * NUMBER_OF_DRONES
