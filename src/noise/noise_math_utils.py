import numpy as np
from numba import njit

from common.model_configs import model_config

DRONE_FLIGHT_ALTITUDE = model_config.drone.flight_altitude_m
DRONE_NOISE_AT_SOURCE = model_config.drone.noise_at_source_db

DRONE_ALTITUDE_SQUARED = DRONE_FLIGHT_ALTITUDE ** 2
BASELINE_NOISE_AT_ALTITUDE = DRONE_NOISE_AT_SOURCE - 20.0 * np.log10(DRONE_FLIGHT_ALTITUDE)
MATH_LOG_10_DIVIDED_BY_10 = np.log(10.0) / 10.0
ZERO_NOISE_SQUARED_DISTANCE = (10.0 ** (0.1 * DRONE_NOISE_AT_SOURCE)) - DRONE_ALTITUDE_SQUARED


@njit
def calculate_distance(delta_northing: float, delta_easting: float, altitude: float) -> float:
    return delta_northing ** 2 + delta_easting ** 2 + altitude ** 2


@njit
def calculate_noise_at_distance(squared_distance: float) -> float:
    return DRONE_NOISE_AT_SOURCE - 10.0 * np.log10(squared_distance)


@njit
def calculate_mixed_noise_level(sound_sources):
    if len(sound_sources) == 0:
        return 0.0

    linear_sum = 0.0
    for source in sound_sources:
        linear_sum += np.exp(source * MATH_LOG_10_DIVIDED_BY_10)

    return 10.0 * np.log10(linear_sum)


@njit
def add_two_decibel_levels(first_dbl_level: float, second_dbl_level: float) -> float:
    return 10.0 * np.log10((10.0 ** (first_dbl_level / 10.0)) + (10.0 ** (second_dbl_level / 10.0)))
