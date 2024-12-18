import matplotlib
matplotlib.use('TkAgg')

import matplotlib.pyplot as plt
from typing import List
from common.coordinate import Coordinate
from drones.drone import Drone
from common.configuration import MAP_LEFT, MAP_RIGHT, MAP_TOP, MAP_BOTTOM
from common.configuration import BACKGROUND_IMAGE_PATH


class Plotter:
    def __init__(self, warehouses: List[Coordinate]):
        self.interactive = True
        self.img = plt.imread(BACKGROUND_IMAGE_PATH)
        self.figure, self.ax = plt.subplots()
        self.ax.xaxis.set_visible(False)
        self.ax.yaxis.set_visible(False)
        self.ax.imshow(self.img, extent=[MAP_LEFT, MAP_RIGHT, MAP_BOTTOM, MAP_TOP])

        # Preparing static plot elements
        self.warehouses_x = [x.longitude for x in warehouses]
        self.warehouses_y = [x.latitude for x in warehouses]
        self.warehouse_scatter = plt.scatter(self.warehouses_x, self.warehouses_y, color='blue', marker='p',
                                             linewidths=5)

        # Initializing dynamic plot elements
        self.drone_scatter = plt.scatter([], [], color='red', linewidths=0.5)
        self.order_scatter = plt.scatter([], [], color='green', marker='v', linewidths=1)

        plt.xlim(MAP_LEFT, MAP_RIGHT)
        plt.ylim(MAP_BOTTOM, MAP_TOP)

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
