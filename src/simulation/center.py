from common.configuration import PLOT_MAP, PLOT_STATISTICS, PRINT_MODEL_STATISTICS, \
    TOTAL_ORDER_NUMBER, TOTAL_DRONE_NUMBER, MODEL_START_TIME, MODEL_TIME_STEP
from common.enum import DroneStatus
from common.file_utils import save_drones_data, save_drone_noise_data, define_results_path
from common.math_utils import get_difference, find_nearest_warehouse_location
from drones.dronegenerator import DroneGenerator
from noise.noise_data_processor import calculate_combined_noise_data
from noise.noise_tracker import NoiseTracker
from orders.order_generator import load_orders
from simulation.planner import PathPlanner
from simulation.plotter import Plotter
from simulation.statistics import plot_noise_difference_colormap, plot_noise_change_barchart, plot_graphs


class Center:
    def __init__(self, warehouses, number_of_orders, number_of_drones):
        self.warehouses = [location for _, location in warehouses]
        
        self.model_time = MODEL_START_TIME
        self.iteration_count = 0

        self.pending_orders = []

        self.free_drones = []
        self.delivering_drones = []
        self.waiting_planning_drones = []

        self.init_orders(number_of_orders)
        self.init_drones(number_of_drones, self.warehouses)

        self.noise_tracker = NoiseTracker()
        self.planner = PathPlanner()

        if PLOT_MAP:
            self.plotter = Plotter(self.warehouses)

    def init_orders(self, number_of_orders):
        print("Initialise orders...")

        orders = load_orders(number_of_orders)

        self.pending_orders.extend(orders)

    def init_drones(self, number_of_drones, warehouses):
        print("Assign drones...")

        drone_generator = DroneGenerator(warehouses)

        drones = drone_generator.generate_drones(number_of_drones)

        self.free_drones.extend(drones)

    def print_drones_statistics(self):
        print(f"Drone Statistics at iteration {self.iteration_count}, time {self.model_time}:")
        print(f"  Pending Orders: {len(self.pending_orders)}")
        print(f"  Free Drones: {len(self.free_drones)}")
        print(f"  Delivering Drones: {len(self.delivering_drones)}")
        print(f"  Waiting Planning Drones: {len(self.waiting_planning_drones)}\n")

    def update_model_time(self):
        self.model_time += MODEL_TIME_STEP
        self.iteration_count += 1

    def run_center(self):
        print("Start the simulation...")

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

        self.track_drones()

        if PLOT_MAP:
            self.plot_drones()

    def process_orders(self):
        while self.has_waiting_order() and self.has_free_drone():
            order = self.pending_orders.pop()
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

    def end_simulation(self):
        print("Simulation completed")

        path = define_results_path(TOTAL_ORDER_NUMBER, TOTAL_DRONE_NUMBER)

        self.noise_tracker.calculate_noise_cells()
        self.save_results(path)

        combined_noise = calculate_combined_noise_data(path)

        if PLOT_STATISTICS:
            plot_noise_difference_colormap(combined_noise)
            plot_noise_change_barchart(combined_noise)
            plot_graphs()

        if PLOT_MAP:
            self.plotter.plot_combined_noise_pollution(combined_noise)
            self.plotter.save_flight_map()

    def save_results(self, path):
        print("Save simulation results...")

        save_drones_data(self.free_drones, path)
        save_drone_noise_data(self.noise_tracker, self.iteration_count, path)

        print("Results saved!")

    def has_free_drone(self):
        return bool(self.free_drones)

    def has_delivering_drones(self):
        return bool(self.delivering_drones)

    def has_waiting_order(self):
        return bool(self.pending_orders)

    def has_planning_drone(self):
        return bool(self.waiting_planning_drones)
