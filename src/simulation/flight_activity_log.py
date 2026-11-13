from collections import Counter


class FlightActivityLog:
    """Counts, per home warehouse, the time steps in which a drone was out on a delivery."""

    def __init__(self):
        self.drone_steps_by_warehouse = Counter()
        self.time_steps_without_drones = 0

    def record(self, delivering_drones):
        if not delivering_drones:
            self.time_steps_without_drones += 1

        self.drone_steps_by_warehouse.update(drone.return_location for drone in delivering_drones)
