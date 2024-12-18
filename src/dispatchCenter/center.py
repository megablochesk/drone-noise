import csv
import os
import time

from cityMap.citymap import Coordinate, CityMap
from common.configuration import CENTER_PER_SLICE_TIME, PLOT_SIMULATION
from common.configuration import MAP_LEFT, MAP_TOP, MAP_RIGHT, MAP_BOTTOM
from common.configuration import ORDERS, DRONES, NOISE_CELL_WIDTH, NOISE_CELL_LENGTH, COST_FUNCTION, PRIORITIZE_K, \
    PRIORITIZE_P
from common.configuration import RESULT_BASE_PATH
from common.configuration import USE_DENSITY_MATRIX
from common.constants import DRONE_ALTITUTE
from common.decorators import auto_str
from common.enum import DroneStatus
from common.math_utils import difference, find_nearest_free_drone
from common.util import Queue
from dispatchCenter.folium_plotter import FoliumPlotter
from dispatchCenter.planner import PathPlanner
from dispatchCenter.plotter import Plotter
from drones.dronegenerator import DroneGenerator
from matrix.noise import DensityMatrix
from orders.order_generator import OrderGenerator


@auto_str
class Center:
    def __init__(self, warehouses, city_map: CityMap, num_orders, num_drones):
        self.warehouses = [Coordinate(latitude=x[0], longitude=x[1]) for x in warehouses]

        self.iteration_count = 0

        self.waiting_orders = Queue()
        self.free_drones = list()
        self.delivering_drones = list()
        self.waiting_planning_drones = list()

        self.init_orders(num_orders)
        self.init_drones(num_drones, self.warehouses)

        self.matrix = DensityMatrix()
        self.planner = PathPlanner(self.matrix)

        if PLOT_SIMULATION:
            self.plotter = Plotter(warehouses=self.warehouses, city_map=city_map)
            self.folium_plotter = FoliumPlotter(warehouses=self.warehouses, city_map=city_map)

    def init_orders(self, number_of_orders):
        print("Start initializing orders...")

        orders = OrderGenerator.load_orders(number_of_orders)

        self.waiting_orders.extend(orders)

    def init_drones(self, num, warehouses):
        print("Start creating drones...")

        drone_generator = DroneGenerator(warehouses)

        drones = drone_generator.generate_drones(num)

        self.free_drones.extend(drones)

    def run_center(self):
        print("Simulation starts, running the center...")

        origin_time = time.time()

        while 1:
            if self.is_time_for_next_iteration(origin_time):
                self.iteration_count += 1

                if self.has_waiting_order() or self.has_delivering_drones():
                    self.process_iteration()

                if self.should_end_simulation():
                    self.end_simulation()
                    break

    def is_time_for_next_iteration(self, origin_time):
        next_iteration_time = origin_time + self.iteration_count * CENTER_PER_SLICE_TIME

        return time.time() > next_iteration_time

    def process_iteration(self):
        self.process_orders()
        self.plan_drones_path()
        self.update_drones()

        if USE_DENSITY_MATRIX:
            self.track_drones_noise()

        if PLOT_SIMULATION:
            self.plot_drones()

    def process_orders(self):

        while self.has_waiting_order() and self.has_free_drone():
            order = self.waiting_orders.pop()
            drone = find_nearest_free_drone(order, self.free_drones)
            drone.accept_order(order)

            self.free_drones.remove(drone)
            self.waiting_planning_drones.append(drone)

    def plan_drones_path(self):
        for drone in self.waiting_planning_drones:
            # NOTE: paths are re-planned at each iteration (to adapt to noise matrix accumulated so far)
            path = self.planner.plan(start=drone.location,
                                     end=drone.destination,
                                     time_count=self.iteration_count)

            drone.receive_path(path)

            if drone not in self.delivering_drones:
                self.delivering_drones.append(drone)
        # Update the list of waiting for planning drones
        self.waiting_planning_drones = difference(self.waiting_planning_drones, self.delivering_drones)

    def update_drones(self):
        """
        Update delivering drones' status and position.
        If any delivering drone completes its order, update its status and move it to the list of free drones.
        """
        for drone in self.delivering_drones:
            drone.update_position()
            if drone.status is DroneStatus.WAITING:
                self.free_drones.append(drone)

        self.delivering_drones = [x for x in self.delivering_drones if x not in self.free_drones]
        self.waiting_planning_drones.extend([x for x in self.delivering_drones if x.need_planning is True])

    def track_drones_noise(self):
        self.matrix.track_noise(self.delivering_drones)

    def plot_drones(self):
        # self.plotter.plot(self.delivering_drones)
        self.folium_plotter.plot(self.delivering_drones)

    def should_end_simulation(self):
        return not (self.has_waiting_order() or self.has_delivering_drones() or self.has_planning_drone())

    def end_simulation(self):
        print("All orders have been completed, no more new orders")

        if USE_DENSITY_MATRIX:
            self.save_results()

    def save_results(self):
        print("Saving results to the local")
        self.save()
        print("Done saving results")

    def save(self):
        # t = datetime.now().strftime("%m-%d_%H:%M:%S")
        # path = RESULT_BASE_PATH + '/' + t
        if COST_FUNCTION == 'first':
            path = RESULT_BASE_PATH + '/' + ("v2_o%d_d%d_k%d_z%d" % (ORDERS, DRONES, PRIORITIZE_K, DRONE_ALTITUTE))
        else:
            path = RESULT_BASE_PATH + '/' + ("v2_o%d_d%d_p%d_z%d" % (ORDERS, DRONES, PRIORITIZE_P, DRONE_ALTITUTE))
        if not os.path.exists(path):
            os.makedirs(path)

        # drone data
        drone_path = path + '/drone.csv'
        drone_fields = ['Drone ID', 'Total Step', 'Total Distance', 'Total Orders']
        drone_data = []
        for drone in self.free_drones:
            drone_data.append([drone.drone_id,
                               drone.tracker.total_step(),
                               drone.tracker.total_distance(),
                               drone.tracker.total_orders()])
        with open(drone_path, 'w') as f:
            write = csv.writer(f)
            write.writerow(drone_fields)
            write.writerows(drone_data)
            print(f'Done writing drones data!')
            f.flush()
            f.close()

        # density matrix matrix data
        matrix_path = path + '/matrix.csv'
        matrix_fields = ['Row',
                         'Col',
                         'Average Noise',
                         'Maximum Noise',
                         'Time']
        matrix_data = []
        for i in range(self.matrix.rows):
            for j in range(self.matrix.cols):
                matrix_data.append([i,
                                    j,
                                    self.matrix.matrix[i][j].total_noise / self.iteration_count,
                                    self.matrix.matrix[i][j].max_noise,
                                    self.iteration_count])
        with open(matrix_path, 'w') as f:
            write = csv.writer(f)
            write.writerow(matrix_fields)
            write.writerows(matrix_data)
            print(f'Done writing matrix density matrix data!')
            f.flush()
            f.close()

        # configuration
        config_path = path + '/config.csv'
        config_fields = ['Left Longitude', 'Right Longitude', 'Top Latitude', 'Bottom Latitude',
                         'Orders', 'Drones',
                         'Cell Length', 'Cell Width',
                         'Rows', 'Cols',
                         'Prioritization K']
        config = [[MAP_LEFT, MAP_RIGHT, MAP_TOP, MAP_BOTTOM,
                   ORDERS, DRONES,
                   NOISE_CELL_LENGTH, NOISE_CELL_WIDTH,
                   self.matrix.rows, self.matrix.cols,
                   PRIORITIZE_K]]
        with open(config_path, 'w') as f:
            write = csv.writer(f)
            write.writerow(config_fields)
            write.writerows(config)
            print(f'Done writing configuration data!')
            f.flush()
            f.close()

    def has_free_drone(self) -> bool:
        return len(self.free_drones) > 0

    def has_delivering_drones(self) -> bool:
        return len(self.delivering_drones) > 0

    def has_waiting_order(self) -> bool:
        return self.waiting_orders.isEmpty() is False

    def has_planning_drone(self) -> bool:
        return len(self.waiting_planning_drones) > 0
