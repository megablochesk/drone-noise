from collections import defaultdict, deque

from orders.order_generator import load_orders


class DeliveryDispatcher:
    def __init__(self, number_of_orders, dataset):
        self.pending_orders_by_warehouse = self.group_orders_by_warehouse(load_orders(number_of_orders, dataset))
        self.pending_orders_number = sum(len(queue) for queue in self.pending_orders_by_warehouse.values())
        self.assigned_orders = []

    @staticmethod
    def group_orders_by_warehouse(orders):
        queues = defaultdict(deque)
        for dataset_position, order in enumerate(orders):
            queues[order.start_location].append((dataset_position, order))
        return queues

    @property
    def has_pending_orders(self):
        return self.pending_orders_number > 0

    @property
    def pending_orders(self):
        positioned_orders = [entry for queue in self.pending_orders_by_warehouse.values() for entry in queue]
        return [order for _, order in sorted(positioned_orders, key=self.dataset_position)]

    def pending_orders_per_warehouse(self):
        return {warehouse: len(queue) for warehouse, queue in self.pending_orders_by_warehouse.items() if queue}

    def process_orders(self, fleet):
        if not self.can_process(fleet):
            return

        drones_by_loc = self.group_free_drones(fleet.free_drones)
        self.assign_orders(drones_by_loc, fleet)
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
        assignments = []
        for warehouse, drones in free_drones.items():
            orders = self.pending_orders_by_warehouse.get(warehouse)
            while drones and orders:
                dataset_position, order = orders.popleft()
                assignments.append((dataset_position, order, drones.pop()))

        # Drones start planning in dataset order, exactly as the former scan over all pending orders did.
        for _, order, drone in sorted(assignments, key=self.dataset_position):
            drone.accept_order(order)
            fleet.waiting_planning_drones.append(drone)
            self.assigned_orders.append(order)

        self.pending_orders_number -= len(assignments)

    @staticmethod
    def dataset_position(positioned_entry):
        return positioned_entry[0]

    @staticmethod
    def update_free_drones_list(drones_grouped_by_location):
        residual_drones = []
        for queue in drones_grouped_by_location.values():
            residual_drones.extend(queue)
        return residual_drones
