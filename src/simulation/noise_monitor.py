from noise.noise_data_processor import combine_base_and_drone_noise
from noise.noise_tracker import NoiseTracker


class NoiseMonitor:
    def __init__(self):
        self.tracker = NoiseTracker()

        self.impact = None

    def capture(self, drones):
        self.tracker.track_drones(drones)

    def finish(self, iterations):
        self.tracker.calculate_noise_cells()

        self.impact = combine_base_and_drone_noise(self.tracker.noise_cells, iterations)
