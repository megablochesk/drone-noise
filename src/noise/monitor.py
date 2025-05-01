from common.file_utils import save_drone_noise_data
from noise.noise_tracker import NoiseTracker
from noise.noise_data_processor import calculate_combined_noise_data

class NoiseMonitor:
    def __init__(self):
        self.tracker = NoiseTracker()
        self.impact = None

    def capture(self, drones):
        self.tracker.track_drones(drones)

    def finish(self, iterations, path):
        self.tracker.calculate_noise_cells()

        save_drone_noise_data(self.tracker, iterations, path)

        self.impact = calculate_combined_noise_data(path)
