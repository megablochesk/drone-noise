from datetime import datetime
from typing import List

from common.configuration import PRINT_DRONE_STATISTICS, MAP_TOP, MAP_LEFT, MAP_RIGHT, MAP_BOTTOM
from common.coordinate import Coordinate
from common.enum import DroneStatus
from common.math_utils import find_nearest_warehouse, calculate_distance
from drones.tracker import Tracker
from orders.order import Order


class Drone:
    def __init__(self, drone_id, warehouses: List[Coordinate], start_location: Coordinate):
        self.drone_id = drone_id
        self.warehouses = warehouses
        self.location = start_location

        self.order = None
        self.status = DroneStatus.WAITING
        self.destination = None
        self.need_planning = True
        self.path = []
        self.tracker = Tracker()
    
    def accept_order(self, order: Order):
        self.order = order
        self.order.mark_as_accepted()
        self.status = DroneStatus.COLLECTING
        self.destination = self.order.start_location

        if PRINT_DRONE_STATISTICS:
            print(f"Drone '{self.drone_id}' accepted order '{self.order.order_id}' and is flying to {self.destination}")
    
    def collect_parcel(self):
        self.order.mark_as_en_route()
        self.status = DroneStatus.DELIVERING
        self.destination = self.order.end_location

        if PRINT_DRONE_STATISTICS:
            print(f"Drone '{self.drone_id}' collected order '{self.order.order_id}' and is flying to {self.destination}")
    
    def complete_delivering(self):
        self.order.mark_as_delivered()
        self.status = DroneStatus.RETURNING
        self.destination = find_nearest_warehouse(self.warehouses, self.location)

        if PRINT_DRONE_STATISTICS:
            print(f"Drone '{self.drone_id}' delivered order '{self.order.order_id} and is flying to {self.destination}")
    
    def return_to_warehouse(self):
        self.status = DroneStatus.WAITING
        self.order = None
        self.destination = None
        self.tracker.record()

        if PRINT_DRONE_STATISTICS:
            print(f"Drone '{self.drone_id}' returned to the nearest warehouse and start to recharge")

    def update_position(self):
        # Drone's status will change: COLLECTING -> DELIVERING -> RETURNING -> WAITING
        if self.is_outside_map_boundary():
            self.handle_out_of_boundary()
        elif self.drone_has_path():
            self.follow_path()
        else:
            self.handle_no_path()

    def handle_out_of_boundary(self):
        if PRINT_DRONE_STATISTICS:
            print(f"ERROR: {self} is out of boundary, {self.order} failed to be delivered, "
                  f"{self} has been sent to the nearest warehouse")

        self.abort_mission()

    def handle_no_path(self):
        if PRINT_DRONE_STATISTICS:
            print(f"WARNING: {self} has no path")

    def follow_path(self):
        self.fly_to_next_coordinate()
        if self.has_reached_destination():
            self.need_planning = True
            self.update_status_on_reach()

    def update_status_on_reach(self):
        if self.status is DroneStatus.COLLECTING:
            self.collect_parcel()
        elif self.status is DroneStatus.DELIVERING:
            self.complete_delivering()
        elif self.status is DroneStatus.RETURNING:
            self.return_to_warehouse()

    def abort_mission(self):
        self.order = None
        self.destination = None
        self.status = DroneStatus.UNASSIGNED

        self.send_to_nearest_warehouse()

    def send_to_nearest_warehouse(self):
        self.location = nearest_neighbor(neighbors=self.warehouses, target=self.location)
    
    def receive_path(self, path):
        self.path = path
        self.need_planning = False
    
    def fly_to_next_coordinate(self):
        next_location = self.path.pop(0)
        distance = calculate_distance(self.location, next_location)

        self.location = next_location

        self.tracker.increment_distance(distance)
        self.tracker.increment_step()
    
    def is_outside_map_boundary(self):
        return not (MAP_BOTTOM <= self.location.northing <= MAP_TOP and
                    MAP_LEFT <= self.location.easting <= MAP_RIGHT)
    
    def drone_has_path(self):
        return bool(self.path)

    def has_reached_destination(self):
        return self.destination is not None and self.location == self.destination
