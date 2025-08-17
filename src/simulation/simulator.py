from common.model_configs import model_config
from common.runtime_configs import runtime_simulation_config as runtime_config
from simulation.dispatcher import Dispatcher
from simulation.fleet import Fleet
from simulation.noise_monitor import NoiseMonitor
from simulation.plotter import Plotter
from simulation.timer import Timer

PRINT_MODEL_STATISTICS = runtime_config.print_model_stats

LONDON_WAREHOUSES = list(model_config.warehouses.bng_coordinates.items())
WAREHOUSES = [location for _, location in LONDON_WAREHOUSES]


class Simulator:
    def __init__(self):
        self.undelivered_orders_number = runtime_config.orders

        self.timer = Timer()
        self.noise_monitor = NoiseMonitor()
        self.fleet = Fleet(runtime_config.drones, runtime_config.default_order_base_path, WAREHOUSES)
        self.dispatcher = Dispatcher(runtime_config.orders, runtime_config.default_order_base_path)
        self.plotter = Plotter(WAREHOUSES)

    @property
    def delivered_orders_number(self):
        return self.undelivered_orders_number - len(self.dispatcher.pending_orders) - len(self.fleet.delivering_drones)

    @property
    def has_pending_deliveries(self):
        return (self.dispatcher.has_pending_orders or
                self.fleet.has_delivering_drones or
                self.fleet.has_planning_drone)

    def run(self):
        print("Running simulation...")

        while self.has_pending_deliveries and self.timer.running:
            if PRINT_MODEL_STATISTICS:
                self.print_drones_statistics()

            self.process_deliveries()

            self.timer.advance()

        self.end_simulation()

    def process_deliveries(self):
        self.dispatcher.process_orders(self.fleet)

        self.fleet.plan_drones_path()
        self.fleet.update_drones()

        self.noise_monitor.capture(self.fleet.delivering_drones)
        self.plotter.update_drones(self.fleet.delivering_drones)

    def end_simulation(self):
        self.noise_monitor.finish(self.timer.iteration)
        self.plotter.plot_noise_map(self.noise_monitor.impact)

        print("Simulation completed!")

    def print_drones_statistics(self):
        print(f"Drone Statistics at iteration {self.timer.iteration}, time {self.timer.now}:")
        print(f"  Pending Orders: {len(self.dispatcher.pending_orders)}")
        print(f"  Delivered Orders: {self.delivered_orders_number}")
        print(f"  Free Drones: {len(self.fleet.free_drones)}")
        print(f"  Delivering Drones: {len(self.fleet.delivering_drones)}")
        print(f"  Waiting Planning Drones: {len(self.fleet.waiting_planning_drones)}\n")
