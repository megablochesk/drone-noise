import folium
from typing import List
from cityMap.citymap import Coordinate, CityMap
from drones.drone import Drone


class FoliumPlotter:
    def __init__(self, warehouses: List[Coordinate], city_map: CityMap):
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
            # Drone marker
            folium.Marker(
                location=[drone.location.latitude, drone.location.longitude],
                icon=folium.Icon(color='red', icon='paper-plane', prefix='fa'),
                popup='Drone'
            ).add_to(self.drone_group)

            # Order start location
            folium.Marker(
                location=[drone.order.start_location.latitude, drone.order.start_location.longitude],
                icon=folium.Icon(color='green', icon='play', prefix='fa'),
                popup='Order Start'
            ).add_to(self.order_group)

            # Order end location
            folium.Marker(
                location=[drone.order.end_location.latitude, drone.order.end_location.longitude],
                icon=folium.Icon(color='green', icon='flag-checkered', prefix='fa'),
                popup='Order End'
            ).add_to(self.order_group)

        # Add the updated FeatureGroups back to the map
        self.map.add_child(self.drone_group)
        self.map.add_child(self.order_group)

        # Display the updated map
        self.display_map()

    def display_map(self):
        self.map.save('drone_delivery_simulation.html')
