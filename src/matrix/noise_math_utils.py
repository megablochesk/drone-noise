import math

from common.configuration import DRONE_NOISE, DRONE_ALTITUTE

DRONE_ALTITUDE_SQUARED = DRONE_ALTITUTE * DRONE_ALTITUTE
NOISE_AT_SOURCE = DRONE_NOISE

BASELINE_NOISE_AT_ALTITUDE = DRONE_NOISE - 20 * math.log10(DRONE_ALTITUTE)
MATH_LOG_10_DIVIDED_BY_10 = math.log(10) / 10


def calculate_noise_at_distance(distance):
    total_distance_squared = distance * distance + DRONE_ALTITUDE_SQUARED

    return NOISE_AT_SOURCE - 10 * math.log10(total_distance_squared)


def calculate_mixed_noise_level(sound_sources):
    if len(sound_sources) == 0:
        return 0

    linear_sum = sum(math.exp(source * MATH_LOG_10_DIVIDED_BY_10) for source in sound_sources)

    return 10 * math.log10(linear_sum)
