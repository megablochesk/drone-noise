from __future__ import annotations

from common.runtime_configs import get_simulation_config
from simulation.delivery_dispatcher import DeliveryDispatcher
from simulation.fleet import Fleet
from simulation.noise_monitor import NoiseMonitor
from simulation.planned_route_cache import PlannedRouteCache
from simulation.plotter import Plotter
from simulation.timer import Timer


class Simulator:
    def __init__(
        self,
        planned_route_cache: PlannedRouteCache | None = None,
        warehouse_locations=None,
    ):
        self.configs = get_simulation_config()

        self.undelivered_orders_number = self.configs.orders_to_process

        model = self.configs.model
        selected_warehouse_locations = warehouse_locations or list(model.warehouses.bng_coordinates.values())

        self.timer = Timer(start=model.time.start_s, end=model.time.end_s, step=model.time.step_s)
        self.noise_monitor = NoiseMonitor()
        self.fleet = Fleet(
            self.configs.number_of_drones,
            self.configs.order_dataset_path,
            selected_warehouse_locations,
            planned_route_cache=planned_route_cache,
        )
        self.dispatcher = DeliveryDispatcher(self.configs.orders_to_process, self.configs.order_dataset_path)
        self.plotter = Plotter(selected_warehouse_locations)

    @property
    def delivered_orders_number(self):
        return (
            self.undelivered_orders_number
            - self.dispatcher.pending_orders_number
            - len(self.fleet.delivering_drones)
        )

    @property
    def has_pending_deliveries(self):
        return (
            self.dispatcher.has_pending_orders
            or self.fleet.has_delivering_drones
            or self.fleet.has_planning_drone
        )

    def run(self):
        print("Running simulation...")
        print(f"Number of drones - {self.configs.number_of_drones}\nNavigation type - {self.configs.navigator_type}")

        while self.has_pending_deliveries and self.timer.running:
            if self.configs.print_model_stats:
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
        self.noise_monitor.finish()
        self.plotter.plot_noise_map(self.noise_monitor.impact)

        print("Simulation completed!")

    def print_drones_statistics(self):
        print(f"Drone Statistics at iteration {self.timer.iteration}, time {self.timer.now}:")
        print(f"  Pending Orders: {self.dispatcher.pending_orders_number}")
        print(f"  Delivered Orders: {self.delivered_orders_number}")
        print(f"  Free Drones: {len(self.fleet.free_drones)}")
        print(f"  Delivering Drones: {len(self.fleet.delivering_drones)}")
        print(f"  Waiting Planning Drones: {len(self.fleet.waiting_planning_drones)}\n")