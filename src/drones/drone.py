from common.configuration import PRINT_DRONE_STATISTICS
from common.coordinate import Coordinate, calculate_distance
from common.enum import DroneStatus
from drones.tracker import Tracker
from orders.order import Order


class Drone:
    def __init__(self, drone_id, start_location: Coordinate):
        self.drone_id = drone_id

        self.current_location = start_location
        self.return_location = start_location
        self.destination = None

        self.order = None
        self.status = DroneStatus.FREE
        self.need_planning = True
        self.path = []
        self.tracker = Tracker()
        
    def receive_path(self, path):
        self.path = path
        self.need_planning = False
    
    def accept_order(self, order: Order):
        self.order = order
        self.destination = self.order.end_location
        self.status = DroneStatus.PREPARING
        self.order.mark_as_accepted()

        if PRINT_DRONE_STATISTICS:
            print(f"Drone {self.drone_id} accepted order {self.order.order_id} and waiting for the route generation")
    
    def start_delivering(self):
        self.order.mark_as_en_route()
        self.status = DroneStatus.DELIVERING

        if PRINT_DRONE_STATISTICS:
            print(f"Drone '{self.drone_id}' is delivering order {self.order.order_id} to {self.destination}")
    
    def complete_delivering(self):
        self.order.mark_as_delivered()
        self.status = DroneStatus.RETURNING
        self.destination = self.return_location

        if PRINT_DRONE_STATISTICS:
            print(f"Drone {self.drone_id} delivered order {self.order.order_id} and is flying to {self.destination}")
    
    def return_to_warehouse(self):
        self.status = DroneStatus.FREE
        self.order = None
        self.destination = None
        self.tracker.record()

        if PRINT_DRONE_STATISTICS:
            print(f"Drone {self.drone_id} returned to the nearest warehouse and start to recharge")
    
    def drone_has_path(self):
        return bool(self.path)
                
    def move_to_next_waypoint(self):
        next_location = self.path.pop(0)
        distance = calculate_distance(self.current_location, next_location)

        self.current_location = next_location

        self.tracker.increment_distance(distance)
        self.tracker.increment_step()
    
    def has_reached_destination(self):
        return self.destination is not None and self.current_location == self.destination

    def update_status_on_reach(self):
        match self.status:
            case DroneStatus.PREPARING:
                self.start_delivering()
            case DroneStatus.DELIVERING:
                self.complete_delivering()
            case DroneStatus.RETURNING:
                self.return_to_warehouse()
                
    def update_position(self):
        if self.drone_has_path():
            self.move_to_next_waypoint()
            if self.has_reached_destination():
                self.need_planning = True
                self.update_status_on_reach()
