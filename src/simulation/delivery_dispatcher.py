from collections import defaultdict, deque

from orders.order_generator import load_orders


class DeliveryDispatcher:
    def __init__(self, number_of_orders, dataset):
        self.pending_orders = load_orders(number_of_orders, dataset)

    @property
    def has_pending_orders(self):
        return bool(self.pending_orders)

    def process_orders(self, fleet):
        if not self.can_process(fleet):
            return

        drones_by_loc = self.group_free_drones(fleet.free_drones)
        self.pending_orders = self.assign_orders(drones_by_loc, fleet)
        fleet.free_drones = self.update_free_drones_list(drones_by_loc)

    def can_process(self, fleet):
        return self.has_pending_orders and fleet.has_free_drone

    @staticmethod
    def group_free_drones(free_drones):
        grouped_free_drones = defaultdict(deque)
        for drone in free_drones:
            grouped_free_drones[drone.current_location].append(drone)
        return grouped_free_drones

    def assign_orders(self, free_drones, fleet):
        remaining_orders = []

        for order in self.pending_orders:
            drones = free_drones.get(order.start_location)
            if drones:
                drone = drones.pop()
                if not drones:
                    del free_drones[order.start_location]

                drone.accept_order(order)
                fleet.waiting_planning_drones.append(drone)
            else:
                remaining_orders.append(order)

        return remaining_orders

    @staticmethod
    def update_free_drones_list(drones_grouped_by_location):
        residual_drones = []
        for queue in drones_grouped_by_location.values():
            residual_drones.extend(queue)
        return residual_drones
