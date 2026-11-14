from __future__ import annotations

import hashlib
import json
from dataclasses import MISSING, dataclass, fields, replace
from enum import Enum

from common.enum import BaselineNoiseMap, NavigationType, NoiseCalculation, OrderDatasetType
from common.model_configs import ModelConfig, model_config
from common.simulation_configs import SimulationConfig

RUN_KEY_LENGTH = 16


class OrderSource(Enum):
    PUBLISHED_DATASET = "published_dataset"
    SEEDED_POOL = "seeded_pool"


class DemandModel(Enum):
    POPULATION = "population"
    AREA = "area"


class FleetAllocation(Enum):
    EQUAL = "equal"
    PROPORTIONAL_TO_ORDERS = "proportional_to_orders"


@dataclass(frozen=True)
class RunSpecification:
    """Everything that distinguishes one revision run from another."""
    stocking: OrderDatasetType
    number_of_drones: int
    terminal_phases: bool

    order_source: OrderSource = OrderSource.SEEDED_POOL
    seed: int = 0
    pool_size: int = 500_000
    demand_model: DemandModel = DemandModel.POPULATION
    depot_layout: str = "actual"
    fleet_allocation: FleetAllocation = FleetAllocation.EQUAL
    noise_calculation: NoiseCalculation = NoiseCalculation.ENERGY_SUM
    baseline_noise_map: BaselineNoiseMap = BaselineNoiseMap.PUBLISHED

    speed_mps: int = model_config.drone.speed_mps
    flight_altitude_m: float = model_config.drone.flight_altitude_m
    noise_at_source_db: float = model_config.drone.noise_at_source_db
    landing_delay_s: int = model_config.drone.landing_delay_s
    minimum_slant_distance_m: float = model_config.drone.minimum_slant_distance_m
    time_step_s: int = model_config.time.step_s
    noise_cell_m: int = model_config.grid.noise_cell_m
    land_once_at_customer: bool = False


def to_plain_value(value):
    return value.value if isinstance(value, Enum) else value


def specification_to_record(specification: RunSpecification) -> dict:
    return {field.name: to_plain_value(getattr(specification, field.name)) for field in fields(specification)}


def select_identifying_values(specification: RunSpecification) -> dict:
    """Required fields plus every optional field that departs from its default.

    Leaving defaults out keeps existing keys valid when a new optional field is added later.
    """
    record = specification_to_record(specification)
    return {
        field.name: record[field.name]
        for field in fields(specification)
        if field.default is MISSING or record[field.name] != to_plain_value(field.default)
    }


def build_run_key(specification: RunSpecification) -> str:
    canonical_text = json.dumps(select_identifying_values(specification), sort_keys=True)
    return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()[:RUN_KEY_LENGTH]


def build_model_config(specification: RunSpecification) -> ModelConfig:
    drone = replace(
        model_config.drone,
        speed_mps=specification.speed_mps,
        flight_altitude_m=specification.flight_altitude_m,
        noise_at_source_db=specification.noise_at_source_db,
        landing_delay_s=specification.landing_delay_s,
        minimum_slant_distance_m=specification.minimum_slant_distance_m,
    )
    return replace(
        model_config, drone=drone, time=replace(model_config.time, step_s=specification.time_step_s),
        grid=replace(model_config.grid, noise_cell_m=specification.noise_cell_m),
    )


def build_simulation_config(
        specification: RunSpecification, order_dataset_path: str, orders_to_process: int
) -> SimulationConfig:
    return SimulationConfig(
        print_model_stats=False,
        orders_to_process=orders_to_process,
        number_of_drones=specification.number_of_drones,
        drone_landing=specification.terminal_phases,
        land_once_at_customer=specification.land_once_at_customer,
        navigator_type=NavigationType.STRAIGHT,
        noise_calculation=specification.noise_calculation,
        baseline_noise_map=specification.baseline_noise_map,
        order_dataset_path=order_dataset_path,
        model=build_model_config(specification),
    )
