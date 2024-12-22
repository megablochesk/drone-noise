import math

from common.configuration import DRONE_NOISE, DRONE_ALTITUTE

DRONE_ALTITUDE_SQUARED = DRONE_ALTITUTE * DRONE_ALTITUTE
NOISE_AT_SOURCE = DRONE_NOISE

BASELINE_NOISE_AT_ALTITUDE = DRONE_NOISE - 20 * math.log10(DRONE_ALTITUTE)


def calculate_noise_at_distance(distance):
    if distance <= 1:
        return BASELINE_NOISE_AT_ALTITUDE

    total_distance_squared = distance * distance + DRONE_ALTITUDE_SQUARED

    return NOISE_AT_SOURCE - 10 * math.log10(total_distance_squared)


def calculate_mixed_noise_level(sound_sources):
    if len(sound_sources) == 0:
        return 0

    linear_sum = sum(math.exp(source * math.log(10) / 10) for source in sound_sources)

    return 10 * math.log10(linear_sum)
