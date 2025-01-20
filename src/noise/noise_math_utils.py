import math
from numba import njit

from common.configuration import DRONE_NOISE_AT_SOURCE, DRONE_ALTITUTE

DRONE_ALTITUTE = float(DRONE_ALTITUTE)
DRONE_NOISE_AT_SOURCE = float(DRONE_NOISE_AT_SOURCE)

DRONE_ALTITUDE_SQUARED = DRONE_ALTITUTE * DRONE_ALTITUTE
BASELINE_NOISE_AT_ALTITUDE = DRONE_NOISE_AT_SOURCE - 20.0 * math.log10(DRONE_ALTITUTE)
MATH_LOG_10_DIVIDED_BY_10 = math.log(10.0) / 10.0
ZERO_NOISE_SQUARED_DISTANCE = (10.0 ** (0.1 * DRONE_NOISE_AT_SOURCE)) - DRONE_ALTITUDE_SQUARED


@njit
def calculate_noise_at_distance(squared_distance):
    return DRONE_NOISE_AT_SOURCE - 10.0 * math.log10(squared_distance + DRONE_ALTITUDE_SQUARED)


@njit
def calculate_mixed_noise_level(sound_sources):
    if len(sound_sources) == 0:
        return 0.0

    linear_sum = 0.0
    for source in sound_sources:
        linear_sum += math.exp(source * MATH_LOG_10_DIVIDED_BY_10)

    return 10.0 * math.log10(linear_sum)


@staticmethod
def add_two_decibel_levels(db1: float, db2: float) -> float:
    return 10 * math.log10((10 ** (db1 / 10)) + (10 ** (db2 / 10)))