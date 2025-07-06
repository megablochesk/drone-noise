from common.file_utils import save_drone_noise_data, define_results_path
from noise.noise_data_processor import calculate_combined_noise_data
from noise.noise_tracker import NoiseTracker


class NoiseMonitor:
    def __init__(self, number_of_drones, number_of_orders):
        self.tracker = NoiseTracker()

        self.path = define_results_path(number_of_orders, number_of_drones)

        self.impact = None

    def capture(self, drones):
        self.tracker.track_drones(drones)

    def finish(self, iterations):
        self.tracker.calculate_noise_cells()

        save_drone_noise_data(self.tracker, iterations, self.path)

        self.impact = calculate_combined_noise_data(self.path)
