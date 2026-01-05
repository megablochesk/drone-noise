from enum import Enum


class OrderStatus(Enum):
    UNASSIGNED = 1
    ACCEPTED = 2
    EN_ROUTE = 3
    DELIVERED = 4


class DroneStatus(Enum):
    FREE = 1
    PREPARING = 2
    DELIVERING = 3
    RETURNING = 4


class NavigationType(Enum):
    STRAIGHT = 0
    HEAVY_NOISE = 1
    LIGHT_NOISE = 2
    MIXED = 3

    MIXED_A025 = 4
    MIXED_A050 = 5
    MIXED_A075 = 6
    MIXED_A100 = 7


class OrderDatasetType(Enum):
    RANDOM = "random"
    FURTHEST = "furthest"
    CLOSEST = "closest"
