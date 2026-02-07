import copy
from typing import List

from common.coordinate import Coordinate
from drones.drone import Drone


class DroneGenerator:
    def __init__(self, warehouses: List[Coordinate]):
        self.warehouses = warehouses
        self._warehouse_index = 0
        self._next_drone_id = 1

    def generate_drones(self, quantity: int) -> List[Drone]:
        drones = []
        for _ in range(quantity):
            drone = self._create_drone()
            drones.append(drone)
            self._advance_warehouse_pointer_by_round_robin()
        return drones

    def _create_drone(self) -> Drone:
        start_location = copy.deepcopy(self.warehouses[self._warehouse_index])
        drone = Drone(
            drone_id=self._next_drone_id,
            start_location=start_location
        )
        self._next_drone_id += 1
        return drone

    def _advance_warehouse_pointer_by_round_robin(self):
        self._warehouse_index = (self._warehouse_index + 1) % len(self.warehouses)
