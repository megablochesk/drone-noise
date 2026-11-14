from dataclasses import replace

import pytest

from common.enum import BaselineNoiseMap, NavigationType, NoiseCalculation, OrderDatasetType
from common.model_configs import model_config
from experiments.revision.run_specification import (
    DemandModel,
    FleetAllocation,
    OrderSource,
    RunSpecification,
    build_model_config,
    build_run_key,
    build_simulation_config,
    specification_to_record,
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
    "navigation": NavigationType.NOISE_A025,
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
    """Field-by-field mapping; routing is straight-line unless the specification says otherwise."""
    specification = replace(BASE_SPECIFICATION, number_of_drones=500, terminal_phases=True)
    config = build_simulation_config(specification, order_dataset_path="orders.csv", orders_to_process=123)
    assert config.number_of_drones == 500
    assert config.drone_landing is True
    assert config.navigator_type.name == "STRAIGHT"
    assert config.noise_calculation is NoiseCalculation.ENERGY_SUM
    assert (config.order_dataset_path, config.orders_to_process) == ("orders.csv", 123)
    assert config.print_model_stats is False


def test_noise_aware_navigation_reaches_the_simulation_configuration():
    specification = replace(BASE_SPECIFICATION, navigation=NavigationType.NOISE_A050)
    config = build_simulation_config(specification, order_dataset_path="orders.csv", orders_to_process=123)
    assert config.navigator_type is NavigationType.NOISE_A050


def test_record_names_the_navigation():
    """The values of the navigation types are bare numbers, so tables carry the name."""
    assert specification_to_record(BASE_SPECIFICATION)["navigation"] == "STRAIGHT"
    assert specification_to_record(replace(BASE_SPECIFICATION, navigation=NavigationType.NOISE_A025))["navigation"] == "NOISE_A025"
    assert specification_to_record(BASE_SPECIFICATION)["stocking"] == "closest"


def test_keys_of_stored_runs_stay_valid_when_a_field_is_added():
    """Key of a stored fine-grid pilot run (results/fine_grid/runs.csv): worst stocking, 500 drones, terminal, seed 1."""
    stored_run = RunSpecification(
        stocking=OrderDatasetType.FURTHEST, number_of_drones=500, terminal_phases=True, seed=1, pool_size=650_000,
        baseline_noise_map=BaselineNoiseMap.ROUND_4_ROAD, time_step_s=10, noise_cell_m=100,
    )
    assert build_run_key(stored_run) == "1cf207546da36ea6"


def test_defaults_are_the_published_values_written_out():
    """The defaults are literals: a key names a run by its difference from the published model, whatever the
    model configuration of the day says. Today both agree."""
    defaults = {name: field.default for name, field in RunSpecification.__dataclass_fields__.items()}

    assert (defaults["speed_mps"], defaults["flight_altitude_m"], defaults["noise_at_source_db"]) == (27, 100.0, 90.0)
    assert (defaults["landing_delay_s"], defaults["minimum_slant_distance_m"]) == (60, 0.0)
    assert (defaults["time_step_s"], defaults["noise_cell_m"]) == (30, 500)
    assert build_model_config(BASE_SPECIFICATION) == model_config


def test_a_run_keeps_its_values_when_the_model_configuration_changes(monkeypatch):
    """A changed default of the model (here a 10 s step and 100 m cells) reaches neither the key of a
    published-design run nor the model it runs with."""
    from experiments.revision import run_specification

    changed_model = replace(
        model_config, time=replace(model_config.time, step_s=10), grid=replace(model_config.grid, noise_cell_m=100)
    )
    key_before = build_run_key(BASE_SPECIFICATION)
    monkeypatch.setattr(run_specification, "model_config", changed_model)

    model = build_model_config(BASE_SPECIFICATION)

    assert build_run_key(BASE_SPECIFICATION) == key_before
    assert (model.time.step_s, model.grid.noise_cell_m) == (30, 500)


def test_a_number_written_as_integer_or_decimal_gives_one_key():
    """10 and 10.0 are the same slant floor and the same time step."""
    floored = replace(BASE_SPECIFICATION, minimum_slant_distance_m=10.0)

    assert build_run_key(replace(BASE_SPECIFICATION, minimum_slant_distance_m=10)) == build_run_key(floored)
    assert build_run_key(replace(BASE_SPECIFICATION, time_step_s=10.0)) == build_run_key(replace(BASE_SPECIFICATION, time_step_s=10))


def test_a_fractional_value_for_a_whole_number_field_is_refused():
    with pytest.raises(ValueError, match="time_step_s"):
        build_run_key(replace(BASE_SPECIFICATION, time_step_s=10.5))
