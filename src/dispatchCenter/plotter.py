import matplotlib
matplotlib.use('TkAgg')

import numpy as np
import matplotlib.pyplot as plt
from typing import List
from cityMap.citymap import Coordinate
from drones.drone import Drone
from cityMap.citymap import CityMap
from common.configuration import BACKGROUND_IMAGE_PATH


class Plotter:
    def __init__(self, warehouses: List[Coordinate], city_map: CityMap):
        self.interactive = True
        self.img = plt.imread(BACKGROUND_IMAGE_PATH)
        self.figure, self.ax = plt.subplots()
        self.ax.xaxis.set_visible(False)
        self.ax.yaxis.set_visible(False)
        self.ax.imshow(self.img, extent=[city_map.left, city_map.right, city_map.bottom, city_map.top])

        # Preparing static plot elements
        self.warehouses_x = [x.longitude for x in warehouses]
        self.warehouses_y = [x.latitude for x in warehouses]
        self.warehouse_scatter = plt.scatter(self.warehouses_x, self.warehouses_y, color='blue', marker='p',
                                             linewidths=5)

        # Initializing dynamic plot elements
        self.drone_scatter = plt.scatter([], [], color='red', linewidths=0.5)
        self.order_scatter = plt.scatter([], [], color='green', marker='v', linewidths=1)

        plt.xlim(city_map.left, city_map.right)
        plt.ylim(city_map.bottom, city_map.top)

        if self.interactive:
            plt.ion()

    def plot(self, drones: List[Drone]):
        """ Update drone and order locations and replot them. """
        if not drones:
            return

        drone_x, drone_y = [], []
        order_x, order_y = [], []

        for drone in drones:
            drone_x.append(drone.location.longitude)
            drone_y.append(drone.location.latitude)
            order_x.append(drone.order.start_location.longitude)
            order_x.append(drone.order.end_location.longitude)
            order_y.append(drone.order.start_location.latitude)
            order_y.append(drone.order.end_location.latitude)

        # Update data for scatter plots
        self.drone_scatter.set_offsets(list(zip(drone_x, drone_y)))
        self.order_scatter.set_offsets(list(zip(order_x, order_y)))

        plt.title("Drone Delivery Simulation")
        plt.pause(0.0001) if self.interactive else plt.show()
