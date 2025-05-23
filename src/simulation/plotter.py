from common.configuration import PLOT_MAP
from visualiser.folium_plotter import FoliumPlotter

class Plotter:
    def __init__(self, warehouse_locations):
        self.enabled = PLOT_MAP
        self.plotter = FoliumPlotter(warehouse_locations) if self.enabled else None

    def update_drones(self, drones):
        if self.enabled:
            self.plotter.plot_drones(drones)

    def plot_noise_map(self, impact):
        if self.enabled:
            self.plotter.plot_combined_noise_pollution(impact)
            self.plotter.save_flight_map()
