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
    UNCACHED_NAVIGATOR = 1
    CACHED_NAVIGATOR = 2
    NOISE_A025 = 4
    NOISE_A050 = 5
    NOISE_A075 = 6
    NOISE_A100 = 7


class LevelAveraging(Enum):
    ARITHMETIC = "arithmetic"  # mean of the decibel values, as the published baseline was aggregated
    ENERGY = "energy"          # level of the mean sound energy


class NoiseCalculation(Enum):
    PER_STEP_LEVELS = "per_step_levels"
    ENERGY_SUM = "energy_sum"


class OrderDatasetType(Enum):
    RANDOM = "random"
    FURTHEST = "furthest"
    CLOSEST = "closest"
