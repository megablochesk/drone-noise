from common.configuration import PRINT_MODEL_STATISTICS


class Simulator:
    def __init__(self, number_of_orders, timer, noise_monitor, fleet, dispatcher, plotter):
        self.undelivered_orders_number = number_of_orders

        self.timer = timer
        self.noise_monitor = noise_monitor
        self.fleet = fleet
        self.dispatcher = dispatcher
        self.plotter = plotter

    @property
    def delivered_orders_number(self):
        return self.undelivered_orders_number - len(self.dispatcher.pending_orders) - len(self.fleet.delivering_drones)

    @property
    def has_pending_deliveries(self):
        return (self.dispatcher.has_pending_orders or
                self.fleet.has_delivering_drones or
                self.fleet.has_planning_drone)

    def run(self):
        print("Start the simulation...")

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
