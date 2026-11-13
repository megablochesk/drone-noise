from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from common.coordinate import Coordinate, calculate_distance


@dataclass(frozen=True)
class RunStatistics:
    delivered_orders: int
    assigned_orders: int
    simulated_duration_s: int
    airborne_drone_seconds: int
    utilisation: float
    drones_by_warehouse: dict[Coordinate, int]
    airborne_drone_seconds_by_warehouse: dict[Coordinate, int]
    utilisation_by_warehouse: dict[Coordinate, float]
    pending_orders_by_warehouse: dict[Coordinate, int]
    time_steps_without_drones: int
    trip_distances_m: np.ndarray


def summarise_run(simulator) -> RunStatistics:
    time_step_s = simulator.timer.step
    simulated_duration_s = simulator.timer.iteration * time_step_s
    drones_by_warehouse = simulator.drones_by_warehouse
    airborne_by_warehouse = {
        warehouse: simulator.activity_log.drone_steps_by_warehouse[warehouse] * time_step_s
        for warehouse in drones_by_warehouse
    }
    airborne_drone_seconds = sum(airborne_by_warehouse.values())

    return RunStatistics(
        delivered_orders=simulator.delivered_orders_number,
        assigned_orders=len(simulator.dispatcher.assigned_orders),
        simulated_duration_s=simulated_duration_s,
        airborne_drone_seconds=airborne_drone_seconds,
        utilisation=airborne_drone_seconds / (sum(drones_by_warehouse.values()) * simulated_duration_s),
        drones_by_warehouse=drones_by_warehouse,
        airborne_drone_seconds_by_warehouse=airborne_by_warehouse,
        utilisation_by_warehouse={
            warehouse: airborne_by_warehouse[warehouse] / (number_of_drones * simulated_duration_s)
            for warehouse, number_of_drones in drones_by_warehouse.items()
        },
        pending_orders_by_warehouse=simulator.dispatcher.pending_orders_per_warehouse(),
        time_steps_without_drones=simulator.activity_log.time_steps_without_drones,
        trip_distances_m=calculate_trip_distances(simulator.dispatcher.assigned_orders),
    )


def calculate_trip_distances(orders) -> np.ndarray:
    """One-way straight-line distance from warehouse to customer for each order."""
    return np.array([calculate_distance(order.start_location, order.end_location) for order in orders])
