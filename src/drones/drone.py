from cityMap.citymap import Coordinate
from orders.order import Order
from common.decorators import auto_str
from common.enum import DroneStatus
from common.math_utils import nearest_neighbor, calculate_distance
from common.constants import DRONE_NOISE
from common.configuration import PRINT_TERMINAL, MAP_TOP, MAP_LEFT, MAP_RIGHT, MAP_BOTTOM
from datetime import datetime
from typing import List
from drones.tracker import Tracker


@auto_str
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
        """
        Drone accepts an order.
        
        Update the order's status from 'WAITING' to 'ACCEPTED'.
        Set a new destination for the drone and calculate speed based on the new destination.
        Update drone's status from 'WAITING' to 'COLLECTING'.
        """
        self.order = order
        self.order.mark_as_accepted()
        self.status = DroneStatus.COLLECTING
        self.destination = self.order.start_location
        if PRINT_TERMINAL:
            print(f"[{datetime.now()}] Drone '{self.drone_id}' accepted Order '{self.order.order_id}'")
            print(f"[{datetime.now()}] Drone '{self.drone_id}' is flying to {self.destination} to pick up food")
    
    def collect_parcel(self):
        """
        Drone collects the food at the start location of the order.
        
        Update the order's status from 'ACCEPTED' to 'DELIVERING'.
        Set a new destination for the drone and calculate speed based on the new destination.
        Update drone's status from 'COLLECTING' to 'DELIVERING'.
        """
        self.order.mark_as_en_route()
        self.status = DroneStatus.DELIVERING
        self.destination = self.order.end_location
        if PRINT_TERMINAL:
            print(f"[{datetime.now()}] Drone '{self.drone_id}' collected Order '{self.order.order_id}'")
            print(f"[{datetime.now()}] Drone '{self.drone_id}' is flying to {self.destination} to deliver food")
    
    def complete_delivering(self):
        """
        Drone complete the delivery to the customer and starts to return to one of warehouses.
        
        Update the order's status from 'DELIVERING' to 'COMPLETE'.
        Find the nearest warehouse and set it as the new destination for the drone,
        and calculate speed based on the new destination.
        Update drone's status from 'DELIVERING' to 'RETURNING'.
        """
        self.order.mark_as_delivered()
        self.status = DroneStatus.RETURNING
        self.destination = nearest_neighbor(neighbors=self.warehouses, target=self.location)
        if PRINT_TERMINAL:
            print(f"[{datetime.now()}] Drone '{self.drone_id}' delivered Order '{self.order.order_id}'")
            print(f"[{datetime.now()}] Drone '{self.drone_id}' is flying to {self.destination} to recharge")
    
    def return_to_warehouse(self):
        """
        Drone arrives at one of the warehouses and start to recharge.
        
        Remove destination and speeds.
        Update drone's status from 'RETURNING' to 'WAITING'.
        Drone is waiting for new orders.
        """
        self.status = DroneStatus.WAITING
        self.order = None
        self.destination = None
        self.tracker.record()
        if PRINT_TERMINAL:
            print(f"[{datetime.now()}] Drone '{self.drone_id}' returned to the nearest warehouse and start to recharge")
            print(f"[{datetime.now()}] Drone '{self.drone_id}' is recharging and waiting for new orders")

    def update_position(self):
        """
        Update drone's position and status based on its current status.

        Drone's status will change: COLLECTING -> DELIVERING -> RETURNING -> WAITING
        """
        if self.is_outside_map_boundary():
            self.handle_out_of_boundary()
        elif self.drone_has_path():
            self.follow_path()
        else:
            self.handle_no_path()

    def handle_out_of_boundary(self):
        if PRINT_TERMINAL:
            print(f"ERROR: {self} is out of boundary, {self.order} failed to be delivered, "
                  f"{self} has been sent to the nearest warehouse")

        self.abort_mission()

    def handle_no_path(self):
        if PRINT_TERMINAL:
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
        """
        Fly to the next coordinate on the path. While flying, use tracker to track step and distance.
        """
        next_location = self.path.pop(0)
        distance = calculate_distance(self.location, next_location)

        self.location = next_location

        self.tracker.increment_distance(distance)
        self.tracker.increment_step()
    
    def is_outside_map_boundary(self):
        """
        Check if the drone is within the boundary of the map
        """
        return not (MAP_BOTTOM <= self.location.latitude <= MAP_TOP and
                    MAP_LEFT <= self.location.longitude <= MAP_RIGHT)
    
    def drone_has_path(self):
        return bool(self.path)

    def has_reached_destination(self):
        """
        Check if the drone has reached the current destination.
        """
        return self.destination is not None and self.location == self.destination
