from common.enum import NoiseCalculation
from common.runtime_configs import get_simulation_config
from noise.energy_noise_tracker import EnergyNoiseTracker
from noise.noise_data_processor import (
    PUBLISHED_CELL_SIZE_M,
    combine_base_and_drone_noise,
    combine_noise_levels,
    load_base_noise_data,
)
from noise.noise_tracker import NoiseTracker


class NoiseMonitor:
    def __init__(self):
        simulation_config = get_simulation_config()
        self.uses_energy_sum = simulation_config.noise_calculation is NoiseCalculation.ENERGY_SUM
        self.baseline_noise_map = simulation_config.baseline_noise_map
        self.cell_size_m = simulation_config.model.grid.noise_cell_m

        if not self.uses_energy_sum and self.cell_size_m != PUBLISHED_CELL_SIZE_M:
            raise ValueError("A noise cell size other than the published one is only supported by the energy-sum noise calculation")

        if not self.uses_energy_sum and simulation_config.model.drone.minimum_slant_distance_m > 0:
            raise ValueError("A minimum slant distance is only supported by the energy-sum noise calculation")

        self.tracker = EnergyNoiseTracker() if self.uses_energy_sum else NoiseTracker()

        self.impact = None

    def capture(self, drones):
        self.tracker.track_drones(drones)

    def finish(self):
        if self.uses_energy_sum:
            self.impact = combine_noise_levels(
                self.tracker.build_drone_noise_dataframe(), load_base_noise_data(self.baseline_noise_map, self.cell_size_m)
            )
            return

        self.tracker.calculate_noise_cells()

        self.impact = combine_base_and_drone_noise(self.tracker.noise_cells, self.baseline_noise_map)
