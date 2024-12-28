import os
from typing import List

import branca
import folium
from common.configuration import MAP_LEFT, MAP_RIGHT, MAP_TOP, MAP_BOTTOM
from common.coordinate import Coordinate
from drones.drone import Drone
from noise.noise_data_processor import NoiseDataProcessor
from noise.noise_overlay_generator import NoiseOverlayGenerator


class Plotter:
    def __init__(self, warehouses: List[Coordinate]):
        center_northing = (MAP_BOTTOM + MAP_TOP) / 2
        center_easting = (MAP_LEFT + MAP_RIGHT) / 2
        center_latlon = Coordinate(center_northing, center_easting).convert_to_latlon()

        self.map = folium.Map(location=center_latlon, zoom_start=13)

        self.drone_group = folium.FeatureGroup(name='Drones')
        self.order_group = folium.FeatureGroup(name='Orders')
        self.warehouse_group = folium.FeatureGroup(name="Warehouses")

        self.map.add_child(self.drone_group)
        self.map.add_child(self.order_group)
        self.map.add_child(self.warehouse_group)

        self.overlay_generator = NoiseOverlayGenerator()
        self.plot_warehouses(warehouses)

    @staticmethod
    def calculate_avg_noise_map(result_path: str):
        matrix_df, config_df = NoiseDataProcessor.read_data(result_path)
        avg_noises, _ = NoiseDataProcessor.generate_density_matrix(matrix_df, config_df)

        return avg_noises

    def plot_noise_pollution_overlay(self, avg_noise_map, img_file='avg_noises.png'):
        self.overlay_generator.create_overlay_image(avg_noise_map, img_file)

        bottom_left_corner = Coordinate(MAP_BOTTOM, MAP_LEFT).convert_to_latlon()
        top_right_corner = Coordinate(MAP_TOP, MAP_RIGHT).convert_to_latlon()

        folium.raster_layers.ImageOverlay(
            name='Average Noise',
            image=img_file,
            bounds=[bottom_left_corner, top_right_corner],
            opacity=0.6,
            interactive=True,
            cross_origin=False,
            zindex=1
        ).add_to(self.map)

        os.remove(img_file)

        color_scale = self.overlay_generator.get_color_scale()
        colormap = branca.colormap.LinearColormap(
            colors=color_scale,
            vmin=self.overlay_generator.min_scale,
            vmax=self.overlay_generator.max_scale,
            caption='Average Noise (dB)'
        )

        colormap.add_to(self.map)
        folium.LayerControl().add_to(self.map)

    def plot_warehouses(self, warehouses: List[Coordinate]):
        for warehouse in warehouses:
            folium.CircleMarker(
                location=warehouse.convert_to_latlon(),
                radius=5,
                color='green',
                fill=True,
                fill_color='green',
                fill_opacity=1.0,
                popup='Warehouse'
            ).add_to(self.warehouse_group)

    def plot_drones(self, drones: List[Drone]):
        for drone in drones:
            folium.CircleMarker(
                location=drone.location.convert_to_latlon(),
                radius=3,
                color='red',
                fill=True,
                fill_color='red',
                fill_opacity=1.0,
                popup=f'Drone {drone.drone_id}'
            ).add_to(self.drone_group)

            folium.CircleMarker(
                location=drone.order.end_location.convert_to_latlon(),
                radius=5,
                color='blue',
                fill=True,
                fill_color='blue',
                fill_opacity=1.0,
                popup=f'Order End {drone.order.order_id}'
            ).add_to(self.order_group)

    def save_flight_map(self, path: str):
        avg_noise_map = self.calculate_avg_noise_map(path)
        self.plot_noise_pollution_overlay(avg_noise_map)

        self.map.save('drone_delivery_simulation.html')
        print("Map has been saved to 'drone_delivery_simulation.html'")
