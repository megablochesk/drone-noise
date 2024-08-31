from enum import Enum


class OrderStatus(Enum):
    UNASSIGNED = 1
    ACCEPTED = 2
    EN_ROUTE = 3
    DELIVERED = 4


class DroneStatus(Enum):
    WAITING = 1
    COLLECTING = 2
    DELIVERING = 3
    RETURNING = 4
