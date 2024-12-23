from typing import List
import os

import branca
import folium
import matplotlib
import numpy as np
import pandas as pd
from PIL import Image
from common.configuration import MAP_LEFT, MAP_RIGHT, MAP_TOP, MAP_BOTTOM
from common.coordinate import Coordinate
from drones.drone import Drone
from matplotlib import cm
from matplotlib.colors import Normalize
from dispatchCenter.plot_noise_pollution import generate_density_matrix, read_data


class FoliumPlotter:
    def __init__(self):
        center_northing = (MAP_BOTTOM + MAP_TOP) / 2
        center_easting = (MAP_LEFT + MAP_RIGHT) / 2

        centroid = Coordinate(center_northing, center_easting).convert_to_latlon()

        self.map = folium.Map(location=centroid, zoom_start=13)

        self.drone_group = folium.FeatureGroup(name='Drones')
        self.order_group = folium.FeatureGroup(name='Orders')
        self.map.add_child(self.drone_group)
        self.map.add_child(self.order_group)

        self.vmin = 25  # Minimum noise level for color scaling
        self.vmax = 75  # Maximum noise level for color scaling
        self.norm = Normalize(vmin=self.vmin, vmax=self.vmax)
        self.colormap = cm.get_cmap('jet')

    @staticmethod
    def calculate_avg_noise_map(result_path):
        matrix_df, config_df, _ = read_data(result_path)

        avg_noises, _ = generate_density_matrix(matrix_df, config_df)
        return avg_noises

    def plot_noise_pollution_overlay(self, avg_noise_map, img_file='avg_noises.png'):
        norm_avg_noises = self.norm(avg_noise_map)
        img = self.colormap(norm_avg_noises)

        img_uint8 = (img * 255).astype(np.uint8)

        img_pil = Image.fromarray(img_uint8)
        img_pil.save(img_file)

        bottom_left_corner = Coordinate(MAP_BOTTOM, MAP_LEFT).convert_to_latlon()
        top_right_corner = Coordinate(MAP_TOP, MAP_RIGHT).convert_to_latlon()

        image_bounds = [bottom_left_corner, top_right_corner]

        folium.raster_layers.ImageOverlay(
            name='Average Noise',
            image=img_file,
            bounds=image_bounds,
            opacity=0.6,
            interactive=True,
            cross_origin=False,
            zindex=1,
        ).add_to(self.map)

        colors = [self.colormap(i) for i in np.linspace(0, 1, 256)]
        colors_hex = [matplotlib.colors.rgb2hex(c) for c in colors]
        colormap = branca.colormap.LinearColormap(
            colors=colors_hex,
            vmin=self.vmin,
            vmax=self.vmax,
            caption='Average Noise (dB)'
        )

        colormap.add_to(self.map)

        folium.LayerControl().add_to(self.map)

        os.remove(img_file)

    def plot(self, drones: List[Drone]):
        for drone in drones:
            folium.CircleMarker(
                location=drone.location.convert_to_latlon(),
                radius=5,
                color='red',
                fill=True,
                fill_color='red',
                fill_opacity=1.0,
                popup=f'Drone {drone.drone_id}'
            ).add_to(self.drone_group)

            folium.CircleMarker(
                location=drone.order.start_location.convert_to_latlon(),
                radius=5,
                color='green',
                fill=True,
                fill_color='green',
                fill_opacity=1.0,
                popup='Order Start'
            ).add_to(self.order_group)

            folium.CircleMarker(
                location=drone.order.end_location.convert_to_latlon(),
                radius=5,
                color='blue',
                fill=True,
                fill_color='blue',
                fill_opacity=1.0,
                popup=f'Order End {drone.order.order_id}'
            ).add_to(self.order_group)

    def save_flight_map(self, path):
        avg_noise_map = self.calculate_avg_noise_map(path)

        self.plot_noise_pollution_overlay(avg_noise_map)

        self.map.save('drone_delivery_simulation.html')
        print("Map has been saved to 'drone_delivery_simulation.html'")
