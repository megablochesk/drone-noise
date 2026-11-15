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


class BaselineNoiseMap(Enum):
    PUBLISHED = "published"                # the banded map of the published results (Defra, 2017 maps)
    ROUND_4_ROAD = "round4_road_laeq16h"   # Defra Round 4 road noise, LAeq,16h, all roads; cell mean of decibels
    ROUND_4_ROAD_ENERGY = "round4_road_laeq16h_energy"  # the same map; cell level of the mean sound energy


class BoundaryDatum(Enum):
    """The datum the latitudes and longitudes of the study boundary file are read on."""
    WGS84 = "wgs84"    # the reading of the published model
    OSGB36 = "osgb36"  # the datum the file is written on


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
