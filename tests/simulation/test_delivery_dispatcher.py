import random
from dataclasses import dataclass, field

import pandas as pd
import pytest

from common.coordinate import Coordinate
from drones.drone import Drone
from simulation.delivery_dispatcher import DeliveryDispatcher
from tests.legacy_reference import load_legacy_module

LEGACY_DISPATCHER_MODULE = load_legacy_module(
    "simulation/delivery_dispatcher.py",
    legacy_dependencies={"orders.order_generator": load_legacy_module("orders/order_generator.py")},
)

WAREHOUSE_A = Coordinate(northing=100.0, easting=100.0)
WAREHOUSE_B = Coordinate(northing=200.0, easting=200.0)
WAREHOUSE_C = Coordinate(northing=300.0, easting=300.0)
DESTINATION = Coordinate(northing=900.0, easting=900.0)


@dataclass
class FleetStub:
    free_drones: list = field(default_factory=list)
    waiting_planning_drones: list = field(default_factory=list)

    @property
    def has_free_drone(self):
        return bool(self.free_drones)


def write_orders(path, order_warehouses: list[Coordinate]) -> str:
    pd.DataFrame({
        "Order ID": range(1, len(order_warehouses) + 1),
        "Start Northing": [warehouse.northing for warehouse in order_warehouses],
        "Start Easting": [warehouse.easting for warehouse in order_warehouses],
        "End Northing": DESTINATION.northing,
        "End Easting": DESTINATION.easting,
    }).to_csv(path, index=False)
    return str(path)


def build_drones(drone_warehouses: list[Coordinate]) -> list[Drone]:
    return [Drone(drone_id, warehouse) for drone_id, warehouse in enumerate(drone_warehouses, start=1)]


def assigned_pairs(fleet: FleetStub) -> list[tuple[int, int]]:
    return [(drone.drone_id, drone.order.order_id) for drone in fleet.waiting_planning_drones]


def pending_order_ids(dispatcher) -> list[int]:
    return [order.order_id for order in dispatcher.pending_orders]


def test_orders_leave_each_warehouse_first_in_first_out(tmp_path):
    """Hand-built case: two free drones at A and none at B, orders A, B, A, A -> orders 1 and 3 fly, 2 and 4 wait."""
    orders_path = write_orders(tmp_path / "orders.csv", [WAREHOUSE_A, WAREHOUSE_B, WAREHOUSE_A, WAREHOUSE_A])
    dispatcher = DeliveryDispatcher(4, orders_path)
    fleet = FleetStub(free_drones=build_drones([WAREHOUSE_A, WAREHOUSE_A]))

    dispatcher.process_orders(fleet)

    assert sorted(order_id for _, order_id in assigned_pairs(fleet)) == [1, 3]
    assert pending_order_ids(dispatcher) == [2, 4]
    assert dispatcher.pending_orders_number == 2
    assert fleet.free_drones == []

    late_drone_at_b = Drone(3, WAREHOUSE_B)
    fleet.free_drones.append(late_drone_at_b)
    dispatcher.process_orders(fleet)

    assert late_drone_at_b.order.order_id == 2
    assert pending_order_ids(dispatcher) == [4]
    assert dispatcher.has_pending_orders


def test_pending_orders_per_warehouse_are_counted(tmp_path):
    """Hand-built case: orders A, B, A, A, C with one drone at A leave A: 2, B: 1, C: 1."""
    orders_path = write_orders(
        tmp_path / "orders.csv", [WAREHOUSE_A, WAREHOUSE_B, WAREHOUSE_A, WAREHOUSE_A, WAREHOUSE_C]
    )
    dispatcher = DeliveryDispatcher(5, orders_path)
    dispatcher.process_orders(FleetStub(free_drones=build_drones([WAREHOUSE_A])))

    assert dispatcher.pending_orders_per_warehouse() == {WAREHOUSE_A: 2, WAREHOUSE_B: 1, WAREHOUSE_C: 1}


def release_random_drones(fleet: FleetStub, generator: random.Random):
    """Mimics drones finishing a round trip: some assigned drones become free again at their warehouse."""
    still_busy = []
    for drone in fleet.waiting_planning_drones:
        if generator.random() < 0.35:
            drone.return_to_warehouse()
            fleet.free_drones.append(drone)
        else:
            still_busy.append(drone)
    fleet.waiting_planning_drones = still_busy


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_assignments_match_the_published_scan_dispatcher(tmp_path, seed):
    """Characterisation: every step is compared with the dispatcher source at the published baseline commit."""
    generator = random.Random(seed)
    warehouses = [WAREHOUSE_A, WAREHOUSE_B, WAREHOUSE_C]
    orders_path = write_orders(tmp_path / "orders.csv", generator.choices(warehouses, weights=[5, 2, 1], k=400))
    drone_warehouses = generator.choices(warehouses, k=25)

    current_dispatcher = DeliveryDispatcher(400, orders_path)
    legacy_dispatcher = LEGACY_DISPATCHER_MODULE.DeliveryDispatcher(400, orders_path)
    current_fleet = FleetStub(free_drones=build_drones(drone_warehouses))
    legacy_fleet = FleetStub(free_drones=build_drones(drone_warehouses))

    for step in range(60):
        current_dispatcher.process_orders(current_fleet)
        legacy_dispatcher.process_orders(legacy_fleet)

        assert assigned_pairs(current_fleet) == assigned_pairs(legacy_fleet)
        assert [drone.drone_id for drone in current_fleet.free_drones] == \
               [drone.drone_id for drone in legacy_fleet.free_drones]
        assert pending_order_ids(current_dispatcher) == pending_order_ids(legacy_dispatcher)
        assert current_dispatcher.has_pending_orders == legacy_dispatcher.has_pending_orders

        release_random_drones(current_fleet, random.Random(seed * 1000 + step))
        release_random_drones(legacy_fleet, random.Random(seed * 1000 + step))
