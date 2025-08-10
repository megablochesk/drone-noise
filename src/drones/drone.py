from common.coordinate import Coordinate
from common.enum import DroneStatus
from orders.order import Order


class Drone:
    def __init__(self, drone_id, start_location: Coordinate):
        self.drone_id = drone_id

        self.current_location = start_location
        self.return_location = start_location
        self.current_altitude = 0
        self.destination = None

        self.order = None
        self.status = DroneStatus.FREE
        self.need_planning = True
        self.route = []
        self.altitudes = []
        
    def assign_route(self, route, altitudes):
        self.route = route
        self.altitudes = altitudes

        self.need_planning = False
    
    def accept_order(self, order: Order):
        self.order = order
        self.destination = self.order.end_location
        self.status = DroneStatus.PREPARING
        self.order.mark_as_accepted()
    
    def start_delivering(self):
        self.order.mark_as_en_route()
        self.status = DroneStatus.DELIVERING
    
    def complete_delivering(self):
        self.order.mark_as_delivered()
        self.status = DroneStatus.RETURNING
        self.destination = self.return_location
    
    def return_to_warehouse(self):
        self.status = DroneStatus.FREE
        self.order = None
        self.destination = None
    
    def drone_has_route(self):
        return bool(self.route)
                
    def move_to_next_waypoint(self):
        self.current_location = self.route.pop(0)
        self.current_altitude = self.altitudes.pop(0)
    
    def has_reached_destination(self):
        return self.destination is not None and not self.route

    def update_status_on_reach(self):
        match self.status:
            case DroneStatus.PREPARING:
                self.start_delivering()
            case DroneStatus.DELIVERING:
                self.complete_delivering()
            case DroneStatus.RETURNING:
                self.return_to_warehouse()
                
    def update_position(self):
        if self.drone_has_route():
            self.move_to_next_waypoint()
            if self.has_reached_destination():
                self.need_planning = True
                self.update_status_on_reach()
