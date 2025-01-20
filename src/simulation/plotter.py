import os
from typing import List

import branca
import folium
from common.configuration import MAP_LEFT, MAP_RIGHT, MAP_TOP, MAP_BOTTOM
from common.coordinate import Coordinate
from drones.drone import Drone
from noise.noise_data_processor import calculate_combined_noise_data

from noise.noise_overlay_generator import get_color_scale, create_noise_layer


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

        self.plot_warehouses(warehouses)

    def plot_combined_noise_pollution(self, combined_noise_df):
        noise_layer, colormap = create_noise_layer(combined_noise_df)

        noise_layer.add_to(self.map)
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
        combined_noise_df = calculate_combined_noise_data(path)
        self.plot_combined_noise_pollution(combined_noise_df)

        self.map.save('drone_delivery_simulation.html')
        print("Map has been saved to 'drone_delivery_simulation.html'")
