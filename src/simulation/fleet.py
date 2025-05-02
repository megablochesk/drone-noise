from common.enum import DroneStatus
from drones.dronegenerator import DroneGenerator
from simulation.planner import PathPlanner


class Fleet:
    def __init__(self, number_of_drones, warehouse_locations):
        self.free_drones = DroneGenerator(warehouse_locations).generate_drones(number_of_drones)
        self.waiting_planning_drones = []
        self.delivering_drones = []

        self.planner = PathPlanner()

    @property
    def has_free_drone(self):
        return bool(self.free_drones)

    @property
    def has_delivering_drones(self):
        return bool(self.delivering_drones)

    @property
    def has_planning_drone(self):
        return bool(self.waiting_planning_drones)

    def plan_drones_path(self):
        for drone in self.waiting_planning_drones:
            path, altitudes = self.planner.plan(start=drone.current_location, end=drone.destination)
            drone.assign_route(path, altitudes)

            if drone not in self.delivering_drones:
                self.delivering_drones.append(drone)

        self.waiting_planning_drones = self.get_difference(self.waiting_planning_drones, self.delivering_drones)

    def update_drones(self):
        for drone in self.delivering_drones:
            drone.update_position()
            if drone.status is DroneStatus.FREE:
                self.free_drones.append(drone)

        self.delivering_drones = [x for x in self.delivering_drones if x not in self.free_drones]
        self.waiting_planning_drones.extend([x for x in self.delivering_drones if x.need_planning is True])

    @staticmethod
    def get_difference(primary_list, exclusion_list):
        return [element for element in primary_list if element not in exclusion_list]
