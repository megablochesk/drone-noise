"""Runs one specification end to end and stores its row, drone-only map and trip log."""
from __future__ import annotations

import time
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from common.coordinate import Coordinate
from common.enum import BaselineNoiseMap
from common.path_configs import get_single_type_order_dataset_pattern
from common.runtime_configs import use_simulation_config
from depots.depot_layouts import resolve_depot_layout
from experiments.revision.result_store import ResultStore, save_result
from experiments.revision.run_specification import (
    FleetAllocation,
    OrderSource,
    RunSpecification,
    build_run_key,
    build_simulation_config,
    specification_to_record,
)
from metrics.cell_table import align_to_grid, load_cell_table
from metrics.exposure_metrics import calculate_mean_noise_increase_db, calculate_newly_exposed_population
from noise.noise_grid import load_noise_grid
from orders.order_loader import load_orders
from orders.seeded_order_pool import (
    PooledOrderQueue,
    assign_warehouse_indices,
    build_order_queues,
    count_orders_per_warehouse,
    load_destination_pool,
)
from simulation.delivery_dispatcher import DeliveryDispatcher
from simulation.fleet_allocation import allocate_fleet_equally, allocate_fleet_in_proportion_to_orders
from simulation.run_statistics import RunStatistics, summarise_run
from simulation.simulator import Simulator

PUBLISHED_ORDERS_IN_DATASET = 100_000
HEADLINE_EXPOSURE_THRESHOLD_DB = 55.0
DELIVERY_RANGE_M = 12_000.0
ORDER_POOLS_DIRECTORY_NAME = "order_pools"


@dataclass(frozen=True)
class PlannedDemand:
    pending_orders_by_warehouse: dict[Coordinate, deque | PooledOrderQueue]
    drone_homes: list[Coordinate]
    pool_orders_by_warehouse: dict[Coordinate, int]


def destination_pool_path(store: ResultStore, specification: RunSpecification) -> Path:
    file_name = (
        f"destinations_{specification.demand_model.value}_seed{specification.seed}_n{specification.pool_size}.parquet"
    )
    return Path(store.root) / ORDER_POOLS_DIRECTORY_NAME / file_name


def published_dataset_path(specification: RunSpecification) -> str:
    return get_single_type_order_dataset_pattern(specification.stocking.value, PUBLISHED_ORDERS_IN_DATASET)


def choose_drone_homes(specification: RunSpecification, order_counts: dict[Coordinate, int]) -> list[Coordinate]:
    if specification.fleet_allocation is FleetAllocation.PROPORTIONAL_TO_ORDERS:
        return allocate_fleet_in_proportion_to_orders(order_counts, specification.number_of_drones)
    return allocate_fleet_equally(order_counts, specification.number_of_drones)


def plan_published_demand(specification: RunSpecification) -> PlannedDemand:
    orders = load_orders(PUBLISHED_ORDERS_IN_DATASET, published_dataset_path(specification))
    pool_orders_by_warehouse = dict(Counter(order.start_location for order in orders))
    return PlannedDemand(
        DeliveryDispatcher.group_orders_by_warehouse(orders),
        choose_drone_homes(specification, pool_orders_by_warehouse), pool_orders_by_warehouse,
    )


def plan_seeded_demand(
        specification: RunSpecification, store: ResultStore, depots: dict[str, Coordinate]
) -> PlannedDemand:
    depot_locations = list(depots.values())
    destinations = load_destination_pool(destination_pool_path(store, specification))
    warehouse_indices = assign_warehouse_indices(destinations, depot_locations, specification.stocking, specification.seed)
    pool_orders_by_warehouse = count_orders_per_warehouse(warehouse_indices, depot_locations)
    return PlannedDemand(
        build_order_queues(destinations, depot_locations, warehouse_indices),
        choose_drone_homes(specification, pool_orders_by_warehouse), pool_orders_by_warehouse,
    )


def plan_demand(specification: RunSpecification, store: ResultStore, depots: dict[str, Coordinate]) -> PlannedDemand:
    if specification.order_source is OrderSource.PUBLISHED_DATASET:
        return plan_published_demand(specification)
    return plan_seeded_demand(specification, store, depots)


def run_simulation(specification: RunSpecification, demand: PlannedDemand) -> Simulator:
    number_of_orders = sum(demand.pool_orders_by_warehouse.values())
    config = build_simulation_config(specification, published_dataset_path(specification), number_of_orders)
    with use_simulation_config(config):
        simulator = Simulator(
            warehouse_locations=demand.drone_homes, pending_orders_by_warehouse=demand.pending_orders_by_warehouse
        )
        simulator.run()
    return simulator


def extract_drone_levels(simulator: Simulator) -> np.ndarray:
    return align_to_grid(load_noise_grid(), simulator.noise_monitor.impact, "average_noise")


def summarise_warehouses(
        statistics: RunStatistics, demand: PlannedDemand, depots: dict[str, Coordinate]
) -> dict[str, dict]:
    """Per depot with orders or drones; orders left refer to the whole pool, not only to the built orders."""
    return {
        depot_name: {
            "drones": statistics.drones_by_warehouse.get(location, 0),
            "airborne_drone_seconds": statistics.airborne_drone_seconds_by_warehouse.get(location, 0),
            "utilisation": statistics.utilisation_by_warehouse.get(location, 0.0),
            "pool_orders": demand.pool_orders_by_warehouse.get(location, 0),
            "orders_left": (
                demand.pool_orders_by_warehouse.get(location, 0)
                - statistics.assigned_orders_by_warehouse.get(location, 0)
            ),
        }
        for depot_name, location in depots.items()
        if location in demand.pool_orders_by_warehouse or location in statistics.drones_by_warehouse
    }


def summarise_exposure(drone_levels_db: np.ndarray, baseline_noise_map: BaselineNoiseMap) -> dict:
    cell_table = load_cell_table(baseline_noise_map)
    return {
        "mean_noise_increase_db": calculate_mean_noise_increase_db(drone_levels_db, cell_table.baseline_levels_db),
        "newly_exposed_population_55db": calculate_newly_exposed_population(
            drone_levels_db, cell_table.baseline_levels_db, cell_table.population, HEADLINE_EXPOSURE_THRESHOLD_DB
        ),
    }


def summarise_operations(statistics: RunStatistics, per_warehouse: dict[str, dict]) -> dict:
    return {
        "delivered_orders": statistics.delivered_orders,
        "assigned_orders": statistics.assigned_orders,
        "orders_left": sum(warehouse["orders_left"] for warehouse in per_warehouse.values()),
        "warehouses_out_of_orders": sum(1 for warehouse in per_warehouse.values() if warehouse["orders_left"] == 0),
        "simulated_duration_s": statistics.simulated_duration_s,
        "airborne_drone_seconds": statistics.airborne_drone_seconds,
        "utilisation": statistics.utilisation,
        "time_steps_without_drones": statistics.time_steps_without_drones,
        "mean_trip_distance_m": np.mean(statistics.trip_distances_m),
        "median_trip_distance_m": np.median(statistics.trip_distances_m),
        "share_of_trips_beyond_delivery_range": np.mean(statistics.trip_distances_m > DELIVERY_RANGE_M),
    }


def build_result_row(
        specification: RunSpecification, git_hash: str, wall_time_s: float, statistics: RunStatistics,
        drone_levels_db: np.ndarray, per_warehouse: dict[str, dict],
) -> dict:
    return {
        "run_key": build_run_key(specification),
        **specification_to_record(specification),
        "git_hash": git_hash,
        "wall_time_s": wall_time_s,
        **summarise_operations(statistics, per_warehouse),
        **summarise_exposure(drone_levels_db, specification.baseline_noise_map),
        "per_warehouse": per_warehouse,
    }


def execute_run(specification: RunSpecification, store: ResultStore, git_hash: str) -> dict:
    started_at_s = time.perf_counter()
    depots = resolve_depot_layout(specification.depot_layout)
    demand = plan_demand(specification, store, depots)
    simulator = run_simulation(specification, demand)
    statistics = summarise_run(simulator)
    drone_levels_db = extract_drone_levels(simulator)
    per_warehouse = summarise_warehouses(statistics, demand, depots)

    wall_time_s = time.perf_counter() - started_at_s
    row = build_result_row(specification, git_hash, wall_time_s, statistics, drone_levels_db, per_warehouse)
    save_result(store, row["run_key"], row, drone_levels_db, statistics.trip_distances_m)
    return row
