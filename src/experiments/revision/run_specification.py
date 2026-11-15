from __future__ import annotations

import hashlib
import json
from dataclasses import MISSING, dataclass, fields, replace
from enum import Enum

from common.enum import BaselineNoiseMap, BoundaryDatum, NavigationType, NoiseCalculation, OrderDatasetType
from common.model_configs import ModelConfig, model_config
from common.simulation_configs import SimulationConfig

RUN_KEY_LENGTH = 16
# The published model, written out: a key names a run by its difference from these values, so it must not
# move with the defaults of the model configuration.
PUBLISHED_SPEED_MPS = 27
PUBLISHED_FLIGHT_ALTITUDE_M = 100.0
PUBLISHED_NOISE_AT_SOURCE_DB = 90.0
PUBLISHED_LANDING_DELAY_S = 60
PUBLISHED_MINIMUM_SLANT_DISTANCE_M = 0.0
PUBLISHED_TIME_STEP_S = 30
PUBLISHED_SIMULATION_END_S = 72_000
PUBLISHED_NOISE_CELL_M = 500
PUBLISHED_BOUNDARY_DATUM = BoundaryDatum.WGS84
NUMBER_TYPES = {"int": int, "float": float}


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

    speed_mps: int = PUBLISHED_SPEED_MPS
    flight_altitude_m: float = PUBLISHED_FLIGHT_ALTITUDE_M
    noise_at_source_db: float = PUBLISHED_NOISE_AT_SOURCE_DB
    landing_delay_s: int = PUBLISHED_LANDING_DELAY_S
    minimum_slant_distance_m: float = PUBLISHED_MINIMUM_SLANT_DISTANCE_M
    time_step_s: int = PUBLISHED_TIME_STEP_S
    noise_cell_m: int = PUBLISHED_NOISE_CELL_M
    land_once_at_customer: bool = False
    navigation: NavigationType = NavigationType.STRAIGHT
    boundary_datum: BoundaryDatum = PUBLISHED_BOUNDARY_DATUM
    simulation_end_s: int = PUBLISHED_SIMULATION_END_S


def to_plain_value(value):
    """Enums by their text value; an enum whose values are bare numbers by its name."""
    if not isinstance(value, Enum):
        return value
    return value.value if isinstance(value.value, str) else value.name


def read_as_declared_number(field_name: str, declared_type: str, value):
    """10 and 10.0 are one value: a number is read in the type its field declares; other values pass through."""
    number_type = NUMBER_TYPES.get(declared_type)
    if number_type is None or isinstance(value, bool):
        return value
    if number_type is int and int(value) != value:
        raise ValueError(f"{field_name} takes whole numbers, got {value}")
    return number_type(value)


def specification_to_record(specification: RunSpecification) -> dict:
    return {
        field.name: to_plain_value(read_as_declared_number(field.name, field.type, getattr(specification, field.name)))
        for field in fields(specification)
    }


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
    time = replace(model_config.time, step_s=specification.time_step_s, end_s=specification.simulation_end_s)
    return replace(
        model_config, drone=drone, time=time,
        grid=replace(
            model_config.grid, noise_cell_m=specification.noise_cell_m, boundary_datum=specification.boundary_datum
        ),
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
        navigator_type=specification.navigation,
        noise_calculation=specification.noise_calculation,
        baseline_noise_map=specification.baseline_noise_map,
        order_dataset_path=order_dataset_path,
        model=build_model_config(specification),
    )
