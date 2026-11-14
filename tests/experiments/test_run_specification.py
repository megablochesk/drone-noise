from dataclasses import replace

import pytest

from common.enum import BaselineNoiseMap, NoiseCalculation, OrderDatasetType
from common.model_configs import model_config
from experiments.revision.run_specification import (
    DemandModel,
    FleetAllocation,
    OrderSource,
    RunSpecification,
    build_model_config,
    build_run_key,
    build_simulation_config,
)

BASE_SPECIFICATION = RunSpecification(stocking=OrderDatasetType.CLOSEST, number_of_drones=1250, terminal_phases=False)

ALTERNATIVE_FIELD_VALUES = {
    "stocking": OrderDatasetType.FURTHEST,
    "number_of_drones": 500,
    "terminal_phases": True,
    "order_source": OrderSource.PUBLISHED_DATASET,
    "seed": 3,
    "pool_size": 100_000,
    "demand_model": DemandModel.AREA,
    "depot_layout": "single_hub",
    "fleet_allocation": FleetAllocation.PROPORTIONAL_TO_ORDERS,
    "noise_calculation": NoiseCalculation.PER_STEP_LEVELS,
    "baseline_noise_map": BaselineNoiseMap.ROUND_4_ROAD,
    "speed_mps": 30,
    "flight_altitude_m": 60.0,
    "noise_at_source_db": 95.6,
    "landing_delay_s": 120,
    "minimum_slant_distance_m": 25.0,
    "time_step_s": 10,
    "noise_cell_m": 100,
    "land_once_at_customer": True,
}


def test_alternative_values_cover_every_field():
    """Guard for the parametrised test below: a new field must get an alternative value here."""
    assert set(ALTERNATIVE_FIELD_VALUES) == set(RunSpecification.__dataclass_fields__)


def test_equal_specifications_share_a_key():
    """Invariant: the key is a pure function of the configuration."""
    same_configuration = RunSpecification(
        stocking=OrderDatasetType.CLOSEST, number_of_drones=1250, terminal_phases=False, seed=0, time_step_s=30
    )
    assert build_run_key(same_configuration) == build_run_key(BASE_SPECIFICATION)


@pytest.mark.parametrize("field_name", sorted(ALTERNATIVE_FIELD_VALUES))
def test_changing_any_field_changes_the_key(field_name):
    """Invariant: two different configurations never share a result."""
    changed = replace(BASE_SPECIFICATION, **{field_name: ALTERNATIVE_FIELD_VALUES[field_name]})
    assert build_run_key(changed) != build_run_key(BASE_SPECIFICATION)


def test_default_specification_keeps_the_published_physical_parameters():
    """Published configuration (ModelConfig defaults): 27 m/s, 100 m, 90 dB, 60 s landing delay, 30 s step."""
    assert build_model_config(BASE_SPECIFICATION) == model_config


def test_overridden_parameters_reach_the_model_configuration():
    """Each override must land in the field of the same meaning; durations stay 10:00-20:00."""
    specification = replace(
        BASE_SPECIFICATION, speed_mps=30, flight_altitude_m=60.0, noise_at_source_db=95.6, landing_delay_s=120,
        minimum_slant_distance_m=25.0, time_step_s=10,
    )
    model = build_model_config(specification)
    assert (model.drone.speed_mps, model.drone.flight_altitude_m, model.drone.noise_at_source_db) == (30, 60.0, 95.6)
    assert (model.drone.landing_delay_s, model.drone.minimum_slant_distance_m, model.time.step_s) == (120, 25.0, 10)
    assert (model.time.start_s, model.time.end_s) == (36_000, 72_000)
    assert model.landing_steps == 12


def test_simulation_configuration_follows_the_specification():
    """Field-by-field mapping; routing is always straight-line in the revision runs."""
    specification = replace(BASE_SPECIFICATION, number_of_drones=500, terminal_phases=True)
    config = build_simulation_config(specification, order_dataset_path="orders.csv", orders_to_process=123)
    assert config.number_of_drones == 500
    assert config.drone_landing is True
    assert config.navigator_type.name == "STRAIGHT"
    assert config.noise_calculation is NoiseCalculation.ENERGY_SUM
    assert (config.order_dataset_path, config.orders_to_process) == ("orders.csv", 123)
    assert config.print_model_stats is False
