import numpy as np
from numba import njit

MATH_LOG_10_DIVIDED_BY_10 = np.log(10.0) / 10.0


@njit
def calculate_distance(delta_northing: float, delta_easting: float, altitude: float) -> float:
    return delta_northing ** 2 + delta_easting ** 2 + altitude ** 2


@njit
def calculate_noise_at_distance(squared_distance: float, noise_at_source_db: float) -> float:
    return noise_at_source_db - 10.0 * np.log10(squared_distance)


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


def calculate_leq(noise_levels_db: np.ndarray) -> float:
    return 10.0 * np.log10(np.mean(10.0 ** (noise_levels_db / 10.0)))


def calculate_sound_exposure_level(noise_levels_db: np.ndarray, time_step_s: float) -> float:
    return 10.0 * np.log10(np.sum(10.0 ** (noise_levels_db / 10.0)) * time_step_s)
