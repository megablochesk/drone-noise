import folium
from typing import List
from cityMap.citymap import Coordinate, CityMap
from drones.drone import Drone

import numpy as np
import pandas as pd
from matplotlib import cm
from matplotlib.colors import Normalize
from PIL import Image
import branca
import matplotlib


class FoliumPlotter:
    def __init__(self, warehouses: List[Coordinate], city_map: CityMap):
        self.city_map = city_map  # Store city_map as an instance variable
        center_latitude = (city_map.bottom + city_map.top) / 2
        center_longitude = (city_map.left + city_map.right) / 2
        self.map = folium.Map(location=[center_latitude, center_longitude], zoom_start=13)

        # Add warehouse markers
        for warehouse in warehouses:
            folium.Marker(
                location=[warehouse.latitude, warehouse.longitude],
                icon=folium.Icon(color='blue', icon='home', prefix='fa'),
                popup='Warehouse'
            ).add_to(self.map)

        # Initialize FeatureGroups for drones and orders
        self.drone_group = folium.FeatureGroup(name='Drones')
        self.order_group = folium.FeatureGroup(name='Orders')
        self.map.add_child(self.drone_group)
        self.map.add_child(self.order_group)

        # Initialize data attributes
        self.avg_noises = None
        self.max_noises = None
        self.std = None
        self.iterations = None
        self.X = None
        self.Y = None
        self.rows = None
        self.cols = None
        self.config = None

        # Initialize normalization and colormap settings
        self.vmin = 25  # Minimum noise level for color scaling
        self.vmax = 60  # Maximum noise level for color scaling
        self.norm = Normalize(vmin=self.vmin, vmax=self.vmax)
        self.colormap = cm.get_cmap('jet')  # Choose your preferred colormap

    def read_data(self, result_path):
        """Read necessary data from CSV files."""
        matrix_df = pd.read_csv(f'{result_path}/matrix.csv')
        config_df = pd.read_csv(f'{result_path}/config.csv')
        drone_df = pd.read_csv(f'{result_path}/drone.csv')
        return matrix_df, config_df, drone_df

    def generate_density_matrix(self, matrix_df, config_df):
        """Generate density matrix from data."""
        config = config_df.iloc[0]
        rows = int(config['Rows'])
        cols = int(config['Cols'])

        la = np.linspace(config['Top Latitude'], config['Bottom Latitude'], rows)
        lo = np.linspace(config['Left Longitude'], config['Right Longitude'], cols)
        avg_noises = matrix_df['Average Noise'].to_numpy().reshape(rows, cols)
        max_noises = matrix_df['Maximum Noise'].to_numpy().reshape(rows, cols)

        std = np.std(avg_noises)
        iterations = int(matrix_df.iloc[0]['Time'])

        X, Y = np.meshgrid(lo, la)

        return avg_noises, max_noises, std, iterations, X, Y, rows, cols, config

    def add_noise_pollution_map(self, result_path):
        """Add noise pollution overlay to the map."""
        # Read data
        matrix_df, config_df, drone_df = self.read_data(result_path)

        # Generate density matrix
        avg_noises, max_noises, std, iterations, X, Y, rows, cols, config = self.generate_density_matrix(
            matrix_df, config_df
        )
        # Store data in instance variables
        self.avg_noises = avg_noises
        self.max_noises = max_noises
        self.std = std
        self.iterations = iterations
        self.X = X
        self.Y = Y
        self.rows = rows
        self.cols = cols
        self.config = config

    def plot_noise_overlay(self):
        """Add the noise overlay to the map."""
        if self.avg_noises is None:
            print("No noise data available. Please call add_noise_pollution_map(result_path) first.")
            return

        # Map boundaries from city_map
        MAP_LEFT = self.city_map.left
        MAP_RIGHT = self.city_map.right
        MAP_TOP = self.city_map.top
        MAP_BOTTOM = self.city_map.bottom

        # Normalize the average noises
        norm_avg_noises = self.norm(self.avg_noises)
        img = self.colormap(norm_avg_noises)

        # Convert to uint8 format
        img_uint8 = (img * 255).astype(np.uint8)

        # Save the image
        img_pil = Image.fromarray(img_uint8)
        img_pil.save('avg_noises.png')

        # Define the image bounds
        bounds = [[MAP_BOTTOM, MAP_LEFT], [MAP_TOP, MAP_RIGHT]]

        # Add the image overlay
        folium.raster_layers.ImageOverlay(
            name='Average Noise',
            image='avg_noises.png',
            bounds=bounds,
            opacity=0.6,
            interactive=True,
            cross_origin=False,
            zindex=1,
        ).add_to(self.map)

        # Create a matching colormap for the colorbar
        colors = [self.colormap(i) for i in np.linspace(0, 1, 256)]
        colors_hex = [matplotlib.colors.rgb2hex(c) for c in colors]
        colormap = branca.colormap.LinearColormap(
            colors=colors_hex,
            vmin=self.vmin,
            vmax=self.vmax,
            caption='Average Noise (dB)'
        )

        # Add the colorbar to the map
        colormap.add_to(self.map)

        # Add layer control
        folium.LayerControl().add_to(self.map)

    def plot(self, drones: List[Drone]):
        # Remove existing FeatureGroups from the map
        if 'Drones' in self.map._children:
            del self.map._children['Drones']
        if 'Orders' in self.map._children:
            del self.map._children['Orders']

        # Recreate the FeatureGroups
        self.drone_group = folium.FeatureGroup(name='Drones')
        self.order_group = folium.FeatureGroup(name='Orders')

        # Add updated drone and order markers
        for drone in drones:
            # Drone marker (red dot)
            folium.CircleMarker(
                location=[drone.location.latitude, drone.location.longitude],
                radius=5,
                color='red',
                fill=True,
                fill_color='red',
                fill_opacity=1.0,
                popup='Drone'
            ).add_to(self.drone_group)

            # Order start location (green dot)
            folium.CircleMarker(
                location=[drone.order.start_location.latitude, drone.order.start_location.longitude],
                radius=5,
                color='green',
                fill=True,
                fill_color='green',
                fill_opacity=1.0,
                popup='Order Start'
            ).add_to(self.order_group)

            # Order end location (blue dot)
            folium.CircleMarker(
                location=[drone.order.end_location.latitude, drone.order.end_location.longitude],
                radius=5,
                color='blue',
                fill=True,
                fill_color='blue',
                fill_opacity=1.0,
                popup='Order End'
            ).add_to(self.order_group)

        # Add the updated FeatureGroups back to the map
        self.map.add_child(self.drone_group)
        self.map.add_child(self.order_group)

        # Plot the noise overlay

        # result_path = r'D:\Work\Projects\Publications\2024\RRAI Projects\Noise pollution\Code\drone-noise\src/recourses/results/experiments/v2_o50_d400_p0_z100'
        # self.add_noise_pollution_map(result_path)

        #self.plot_noise_overlay()

        # Display the updated map
        self.display_map()

    def display_map(self):
        self.map.save('drone_delivery_simulation.html')
        print("Map has been saved to 'drone_delivery_simulation.html'")
