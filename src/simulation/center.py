import csv
import os

from common.configuration import NOISE_MATRIX_CELL_WIDTH, NOISE_MATRIX_CELL_LENGTH, \
                                 MAP_LEFT, MAP_TOP, MAP_RIGHT, MAP_BOTTOM, \
                                 RESULT_BASE_PATH, USE_DENSITY_MATRIX, PLOT_SIMULATION, DRONE_ALTITUTE, \
                                 TOTAL_ORDER_NUMBER, TOTAL_DRONE_NUMBER, PRINT_MODEL_STATISTICS, MODEL_START_TIME, MODEL_TIME_STEP
from common.coordinate import Coordinate
from common.enum import DroneStatus
from common.math_utils import get_difference, find_nearest_warehouse_location
from simulation.plotter import Plotter
from simulation.planner import PathPlanner
from drones.dronegenerator import DroneGenerator
from noise.noise_tracker import NoiseTracker
from orders.order_generator import OrderGenerator


class Center:
    def __init__(self, warehouses, number_of_orders, number_of_drones):
        self.warehouses = [Coordinate(northing=coords[0], easting=coords[1]) for _, coords in warehouses]
        
        self.model_time = MODEL_START_TIME
        self.iteration_count = 0

        self.waiting_orders = []
        self.free_drones = []
        self.delivering_drones = []
        self.waiting_planning_drones = []

        self.init_orders(number_of_orders)
        self.init_drones(number_of_drones, self.warehouses)

        self.noise_tracker = NoiseTracker()
        self.planner = PathPlanner()

        if PLOT_SIMULATION:
            self.plotter = Plotter(self.warehouses)

    def init_orders(self, number_of_orders):
        print("Start initializing orders...")

        orders = OrderGenerator.load_orders(number_of_orders)

        self.waiting_orders.extend(orders)

    def init_drones(self, number_of_drones, warehouses):
        print("Start creating drones...")

        drone_generator = DroneGenerator(warehouses)

        drones = drone_generator.generate_drones(number_of_drones)

        self.free_drones.extend(drones)

    def print_drones_statistics(self):
        print(f"Drone Statistics at iteration {self.iteration_count}, time {self.model_time}:")
        print(f"  Waiting Orders: {len(self.waiting_orders)}")
        print(f"  Free Drones: {len(self.free_drones)}")
        print(f"  Delivering Drones: {len(self.delivering_drones)}")
        print(f"  Waiting Planning Drones: {len(self.waiting_planning_drones)}\n")

    def update_model_time(self):
        self.model_time += MODEL_TIME_STEP
        self.iteration_count += 1

    def run_center(self):
        print("Simulation starts, running the center...")

        while 1:
            if PRINT_MODEL_STATISTICS:
                self.print_drones_statistics()

            if self.has_waiting_order() or self.has_delivering_drones():
                self.process_iteration()

            self.update_model_time()

            if self.should_end_simulation():
                self.end_simulation()
                break

    def process_iteration(self):
        self.process_orders()
        self.plan_drones_path()
        self.update_drones()

        if USE_DENSITY_MATRIX:
            self.track_drones()

        if PLOT_SIMULATION:
            self.plot_drones()

    def process_orders(self):
        while self.has_waiting_order() and self.has_free_drone():
            order = self.waiting_orders.pop()
            drone = self.find_nearest_free_drone(order, self.free_drones)
            drone.accept_order(order)

            self.free_drones.remove(drone)
            self.waiting_planning_drones.append(drone)

    @staticmethod
    def find_nearest_free_drone(order, free_drones):
        return free_drones[find_nearest_warehouse_location(
            warehouses=[x.location for x in free_drones],
            current_location=order.start_location)]

    def plan_drones_path(self):
        for drone in self.waiting_planning_drones:
            path = self.planner.plan(start=drone.location, end=drone.destination)
            drone.receive_path(path)

            if drone not in self.delivering_drones:
                self.delivering_drones.append(drone)

        self.waiting_planning_drones = get_difference(self.waiting_planning_drones, self.delivering_drones)

    def update_drones(self):
        for drone in self.delivering_drones:
            drone.update_position()
            if drone.status is DroneStatus.WAITING:
                self.free_drones.append(drone)

        self.delivering_drones = [x for x in self.delivering_drones if x not in self.free_drones]
        self.waiting_planning_drones.extend([x for x in self.delivering_drones if x.need_planning is True])

    def track_drones(self):
        self.noise_tracker.track_drones(self.delivering_drones)

    def plot_drones(self):
        self.plotter.plot_drones(self.delivering_drones)

    def should_end_simulation(self):
        return not (self.has_waiting_order() or self.has_delivering_drones() or self.has_planning_drone())

    @staticmethod
    def define_folder_path():
        path = RESULT_BASE_PATH + '/' + f"stat_o{TOTAL_ORDER_NUMBER}_d{TOTAL_DRONE_NUMBER}_alt{DRONE_ALTITUTE}"

        if not os.path.exists(path):
            os.makedirs(path)

        return path

    def end_simulation(self):
        print("All orders have been completed, no more new orders")

        path = self.define_folder_path()

        if USE_DENSITY_MATRIX:
            self.noise_tracker.calculate_noise_matrix()
            self.save_results(path)

        if PLOT_SIMULATION:
            self.plotter.save_flight_map(path)

    def save_results(self, path):
        print("Saving results to the local:")

        self.save_drones_data(path)
        self.save_drone_noise_data(path)
        self.save_configuration_data(path)

        print("Results saved!")

    def save_drones_data(self, path):
        drone_path = f"{path}/drone.csv"
        drone_fields = ['Drone ID', 'Total Step', 'Total Distance', 'Total Orders']
        drone_data = [
            [
                drone.drone_id,
                drone.tracker.total_step(),
                drone.tracker.total_distance(),
                drone.tracker.total_orders()
            ]
            for drone in self.free_drones
        ]
        self.write_csv(drone_path, drone_fields, drone_data, 'drones data')

    def save_drone_noise_data(self, path):
        matrix_path = f"{path}/noise.csv"
        matrix_fields = ['row', 'col', 'avg_noise', 'max_noise']
        matrix_data = [
            [
                i, j,
                self.noise_tracker.noise_matrix[i][j].total_noise / self.iteration_count,
                self.noise_tracker.noise_matrix[i][j].max_noise
            ]
            for i in range(self.noise_tracker.rows)
            for j in range(self.noise_tracker.cols)
        ]
        self.write_csv(matrix_path, matrix_fields, matrix_data, 'noise data')

    def save_configuration_data(self, path):
        config_path = f"{path}/config.csv"
        config_fields = ['Left Longitude', 'Right Longitude', 'Top Latitude', 'Bottom Latitude',
                         'Orders', 'Drones',
                         'Cell Length', 'Cell Width',
                         'Rows', 'Cols']
        config = [[
            MAP_LEFT, MAP_RIGHT, MAP_TOP, MAP_BOTTOM,
            TOTAL_ORDER_NUMBER, TOTAL_DRONE_NUMBER,
            NOISE_MATRIX_CELL_LENGTH, NOISE_MATRIX_CELL_WIDTH,
            self.noise_tracker.rows, self.noise_tracker.cols
        ]]
        self.write_csv(config_path, config_fields, config, 'configuration data')

    @staticmethod
    def write_csv(file_path, headers, data, data_type):
        with open(file_path, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)
            print(f"Done writing {data_type}!")
            f.flush()

    def has_free_drone(self):
        return bool(self.free_drones)

    def has_delivering_drones(self):
        return bool(self.delivering_drones)

    def has_waiting_order(self):
        return bool(self.waiting_orders)

    def has_planning_drone(self):
        return bool(self.waiting_planning_drones)
