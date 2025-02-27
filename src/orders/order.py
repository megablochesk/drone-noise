from dataclasses import dataclass

from common.coordinate import Coordinate
from common.enum import OrderStatus


@dataclass
class Order:
    order_id: int
    start_location: Coordinate
    end_location: Coordinate
    status: OrderStatus = OrderStatus.UNASSIGNED

    def update_status(self, new_status: OrderStatus):
        self.status = new_status

    def mark_as_accepted(self):
        self.update_status(OrderStatus.ACCEPTED)

    def mark_as_en_route(self):
        self.update_status(OrderStatus.EN_ROUTE)

    def mark_as_delivered(self):
        self.update_status(OrderStatus.DELIVERED)
