import numpy as np
import pandas as pd

from common.runtime_configs import get_simulation_config
from noise.energy_noise import FlightSamples, calculate_equivalent_levels_db, sum_inverse_squared_distances
from noise.noise_grid import load_noise_grid


class EnergyNoiseTracker:
    """Accumulates drone positions and converts them to equivalent levels in one energy sum per cell.

    Unlike the per-step tracker, a time step without any drone contributes no energy (the per-step tracker
    records such a step as 0 dB).
    """

    def __init__(self):
        drone = get_simulation_config().model.drone
        self.noise_at_source_db = drone.noise_at_source_db
        self.minimum_slant_distance_m = drone.minimum_slant_distance_m

        self.grid = load_noise_grid()
        self.number_of_time_steps = 0

        self._northings: list[float] = []
        self._eastings: list[float] = []
        self._altitudes_m: list[float] = []

    def track_drones(self, drones):
        self._northings.extend(drone.current_location.northing for drone in drones)
        self._eastings.extend(drone.current_location.easting for drone in drones)
        self._altitudes_m.extend(drone.current_altitude for drone in drones)
        self.number_of_time_steps += 1

    @property
    def samples(self) -> FlightSamples:
        return FlightSamples(
            northings=np.array(self._northings, dtype=np.float64),
            eastings=np.array(self._eastings, dtype=np.float64),
            altitudes_m=np.array(self._altitudes_m, dtype=np.float64),
        )

    def calculate_drone_noise_levels(self) -> np.ndarray:
        inverse_squared_distance_sums = sum_inverse_squared_distances(
            self.grid.centroid_northings, self.grid.centroid_eastings, self.samples,
            minimum_slant_distance_m=self.minimum_slant_distance_m, maximum_slant_distance_m=np.inf,
        )
        return calculate_equivalent_levels_db(
            inverse_squared_distance_sums, self.noise_at_source_db, self.number_of_time_steps
        )

    def build_drone_noise_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame({
            "row": self.grid.rows,
            "col": self.grid.columns,
            "average_noise": self.calculate_drone_noise_levels(),
        }).set_index(["row", "col"])
