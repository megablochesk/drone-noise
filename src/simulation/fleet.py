from __future__ import annotations

from common.enum import DroneStatus
from drones.drone_generator import DroneGenerator
from simulation.planner import PathPlanner


class Fleet:
    def __init__(self, number_of_drones, dataset_path, warehouse_locations):
        self.free_drones = DroneGenerator(warehouse_locations).generate_drones(number_of_drones)
        self.waiting_planning_drones = []
        self.delivering_drones = []

        self.planner = PathPlanner(dataset_path)

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
            self._plan_for_drone(drone)

            if drone not in self.delivering_drones:
                self.delivering_drones.append(drone)

        self.waiting_planning_drones = self._get_difference(self.waiting_planning_drones, self.delivering_drones)

    def _plan_for_drone(self, drone):
        if drone.status is DroneStatus.RETURNING:
            cached = drone.pop_pending_return_leg()
            if cached is not None:
                route, altitudes = cached
                drone.assign_route(route, altitudes)
                return

        route, altitudes = self.planner.plan(start=drone.current_location, end=drone.destination)
        drone.assign_route(route, altitudes)

        if drone.status is DroneStatus.PREPARING:
            self._store_return_leg_from_outbound(drone, route, altitudes)

    @staticmethod
    def _store_return_leg_from_outbound(drone, outbound_route, outbound_altitudes):
        if not outbound_route:
            return

        return_route = list(reversed(outbound_route))
        return_altitudes = list(reversed(outbound_altitudes)) if outbound_altitudes else []

        drone.set_pending_return_leg(return_route, return_altitudes)

    def update_drones(self):
        for drone in self.delivering_drones:
            drone.update_position()
            if drone.status is DroneStatus.FREE:
                self.free_drones.append(drone)

        self.delivering_drones = [x for x in self.delivering_drones if x not in self.free_drones]
        self.waiting_planning_drones.extend([x for x in self.delivering_drones if x.need_planning is True])

    @staticmethod
    def _get_difference(primary_list, exclusion_list):
        return [element for element in primary_list if element not in exclusion_list]
