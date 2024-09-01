from cityMap.citymap import Coordinate
from common.decorators import auto_str
from drones.drone import Drone
from typing import List
import copy



@auto_str
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
            self._advance_warehouse_pointer()
        return drones

    def _create_drone(self) -> Drone:
        start_location = copy.deepcopy(self.warehouses[self._warehouse_index])
        drone = Drone(
            drone_id=self._next_drone_id,
            warehouses=self.warehouses,
            start_location=start_location,
            height=0
        )
        self._next_drone_id += 1
        return drone

    def _advance_warehouse_pointer(self):
        """Advance the warehouse pointer to the next warehouse in a Round Robin manner."""
        self._warehouse_index = (self._warehouse_index + 1) % len(self.warehouses)
