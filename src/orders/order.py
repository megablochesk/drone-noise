from cityMap.citymap import Coordinate
from common.decorators import auto_str
from common.enum import OrderStatus
from datetime import datetime


@auto_str
class Order:
    def __init__(self, order_id, start_location: Coordinate, end_location: Coordinate):
        self.order_id = order_id
        self.start_location = start_location
        self.end_location = end_location
        self.delivery_time = None
        self.status = OrderStatus.UNASSIGNED
    
    def update_status(self, new_status: OrderStatus):
        self.status = new_status
        # self._log_status_change(new_status)

    def mark_as_accepted(self):
        self.update_status(OrderStatus.ACCEPTED)

    def mark_as_en_route(self):
        self.update_status(OrderStatus.EN_ROUTE)

    def mark_as_delivered(self):
        self.delivery_time = datetime.now()
        self.update_status(OrderStatus.DELIVERED)

    def _log_status_change(self, new_status: OrderStatus):
        print(f"[{datetime.now()}] Order '{self.order_id}' status changed to {new_status.value}")
