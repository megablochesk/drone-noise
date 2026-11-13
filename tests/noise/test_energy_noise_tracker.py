from dataclasses import dataclass, replace

import numpy as np
import pytest

from common.coordinate import Coordinate
from common.enum import NoiseCalculation
from common.model_configs import model_config
from common.runtime_configs import use_simulation_config
from common.simulation_configs import SimulationConfig
from noise.energy_noise_tracker import EnergyNoiseTracker
from noise.noise_grid import load_noise_grid
from simulation.noise_monitor import NoiseMonitor
from tests.simulation.simulation_helpers import (
    destination_east_of_warehouse,
    model_with_duration,
    run_small_simulation,
    write_order_dataset,
)

ENERGY_SUM_CONFIG = SimulationConfig(noise_calculation=NoiseCalculation.ENERGY_SUM)


@dataclass
class DroneStub:
    current_location: Coordinate
    current_altitude: float


def test_tracker_flattens_positions_and_counts_time_steps():
    """Hand-built case: two drones in step one and one in step two give three samples over two steps."""
    with use_simulation_config(ENERGY_SUM_CONFIG):
        tracker = EnergyNoiseTracker()
    tracker.track_drones([DroneStub(Coordinate(1.0, 2.0), 100.0), DroneStub(Coordinate(3.0, 4.0), 50.0)])
    tracker.track_drones([DroneStub(Coordinate(5.0, 6.0), 0.0)])

    samples = tracker.samples
    assert tracker.number_of_time_steps == 2
    np.testing.assert_array_equal(samples.northings, [1.0, 3.0, 5.0])
    np.testing.assert_array_equal(samples.eastings, [2.0, 4.0, 6.0])
    np.testing.assert_array_equal(samples.altitudes_m, [100.0, 50.0, 0.0])


def test_drone_hovering_over_a_cell_centroid_gives_fifty_decibels_there():
    """Hand calculation: 90 dB source held 100 m above the centroid for every step is 90 - 40 = 50 dB."""
    grid = load_noise_grid()
    hover_location = Coordinate(grid.centroid_northings[0], grid.centroid_eastings[0])
    with use_simulation_config(ENERGY_SUM_CONFIG):
        tracker = EnergyNoiseTracker()
    for _ in range(4):
        tracker.track_drones([DroneStub(hover_location, 100.0)])

    assert tracker.calculate_drone_noise_levels()[0] == pytest.approx(50.0, abs=1e-9)


def test_minimum_slant_distance_is_rejected_by_the_per_step_calculation():
    """The published per-step path has no distance floor, so asking for one there must fail loudly."""
    floored_model = replace(model_config, drone=replace(model_config.drone, minimum_slant_distance_m=10.0))
    with use_simulation_config(SimulationConfig(model=floored_model)):
        with pytest.raises(ValueError, match="minimum slant distance"):
            NoiseMonitor()


@pytest.mark.parametrize("terminal_phases", [False, True])
def test_energy_sum_map_matches_the_per_step_map_in_a_small_simulation(tmp_path, terminal_phases):
    """Characterisation: same run through the published per-step path and the energy-sum path."""
    destinations = [destination_east_of_warehouse(distance_m) for distance_m in (2_500.0, 6_100.0, 9_000.0)] * 30
    orders_path = write_order_dataset(tmp_path / "orders.csv", destinations)
    base_config = SimulationConfig(
        order_dataset_path=orders_path, orders_to_process=90, number_of_drones=3, print_model_stats=False,
        drone_landing=terminal_phases, model=model_with_duration(3_600),
    )

    per_step_run = run_small_simulation(base_config)
    energy_run = run_small_simulation(base_config.with_overrides(noise_calculation=NoiseCalculation.ENERGY_SUM))

    assert energy_run.delivered_orders_number == per_step_run.delivered_orders_number
    per_step_map = per_step_run.noise_monitor.impact.set_index(["row", "col"]).sort_index()
    energy_map = energy_run.noise_monitor.impact.set_index(["row", "col"]).sort_index()
    assert energy_map.index.equals(per_step_map.index)
    for column in ["average_noise", "combined_noise", "noise_difference"]:
        np.testing.assert_allclose(energy_map[column], per_step_map[column], rtol=0, atol=1e-9)
