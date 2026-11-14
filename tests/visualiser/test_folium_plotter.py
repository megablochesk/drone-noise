"""The simulation snapshot (Figure 2 of the paper) is an interactive map saved as HTML."""
import folium

from common.path_configs import PATH_CONFIGS
from visualiser.folium_plotter import FoliumPlotter


class RecordingMap(folium.Map):
    def save(self, outfile, **kwargs):
        self.saved_to = outfile


def test_flight_map_is_saved_to_the_configured_file():
    plotter = FoliumPlotter.__new__(FoliumPlotter)
    plotter.map = RecordingMap(location=[51.5, -0.1])

    plotter.save_flight_map()

    assert plotter.map.saved_to == PATH_CONFIGS.map_file_path
