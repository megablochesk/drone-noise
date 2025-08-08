import math
import time

import numpy as np
from memory_profiler import memory_usage
from numba import njit

# For demonstration, define needed constants here
DRONE_NOISE_AT_SOURCE = 70.0
DRONE_ALTITUTE = 100.0
DRONE_ALTITUDE_SQUARED = DRONE_ALTITUTE ** 2
MATH_LOG_10_DIVIDED_BY_10 = np.log(10.0) / 10.0

# Example values for M_2_LONGITUDE, M_2_LATITUDE
M_2_LONGITUDE = 8.983111749910169e-06
M_2_LATITUDE = 1.198422790191354e-05


@njit
def calculate_squared_distance(x_distance: float, y_distance: float) -> float:
    return x_distance ** 2 + y_distance ** 2


@njit
def calculate_noise_at_distance_new(squared_distance: float) -> float:
    return DRONE_NOISE_AT_SOURCE - 10.0 * np.log10(squared_distance + DRONE_ALTITUDE_SQUARED)


@njit
def calculate_mixed_noise_level_new(sound_sources) -> float:
    if len(sound_sources) == 0:
        return 0.0
    linear_sum = 0.0
    for source in sound_sources:
        linear_sum += np.exp(source * MATH_LOG_10_DIVIDED_BY_10)
    return 10.0 * np.log10(linear_sum)


def calculate_noise_at_distance_old(x_dist, y_dist):
    if abs(x_dist) + abs(y_dist) == 0:
        if DRONE_ALTITUTE <= 0:
            return DRONE_NOISE_AT_SOURCE
        else:
            return DRONE_NOISE_AT_SOURCE - abs(10 * math.log10(DRONE_ALTITUTE**2))
    else:
        return DRONE_NOISE_AT_SOURCE - abs(
            10 * math.log10(
                (x_dist / M_2_LONGITUDE) ** 2
                + (y_dist / M_2_LATITUDE) ** 2
                + (DRONE_ALTITUTE ** 2)
            )
        )


def calculate_mixed_noise_level_old(sound_sources):
    if sound_sources is None or len(sound_sources) == 0:
        return 0
    summation = 0
    for source in sound_sources:
        summation += np.power(10, source / 10)
    return 10 * np.log10(summation)


def run_speed_test(n_points=10_000_00):
    xs = np.random.uniform(-1000, 1000, n_points)
    ys = np.random.uniform(-1000, 1000, n_points)

    t0 = time.time()
    for x, y in zip(xs, ys):
        _ = calculate_noise_at_distance_old(x, y)
    old_time = time.time() - t0

    _ = calculate_noise_at_distance_new(calculate_squared_distance(xs[0], ys[0]))

    t1 = time.time()
    for x, y in zip(xs, ys):
        sqd = calculate_squared_distance(x, y)
        _ = calculate_noise_at_distance_new(sqd)
    new_time = time.time() - t1

    return old_time, new_time


def run_memory_test(n_points=100000):
    xs = np.random.uniform(-1000, 1000, n_points)
    ys = np.random.uniform(-1000, 1000, n_points)

    def old_methods():
        for x, y in zip(xs, ys):
            _ = calculate_noise_at_distance_old(x, y)

    def new_methods():
        for x, y in zip(xs, ys):
            sqd = calculate_squared_distance(x, y)
            _ = calculate_noise_at_distance_new(sqd)

    old_mem = max(memory_usage((old_methods, ), max_iterations=1, interval=0.01))

    _ = calculate_noise_at_distance_new(calculate_squared_distance(xs[0], ys[0]))
    new_mem = max(memory_usage((new_methods, ), max_iterations=1, interval=0.01))

    return old_mem, new_mem


if __name__ == "__main__":
    old_time, new_time = run_speed_test()
    print(f"Time (old vs new): {old_time:.4f}s vs {new_time:.4f}s")

    old_mem, new_mem = run_memory_test()
    print(f"Memory (old vs new): {old_mem:.2f}MB vs {new_mem:.2f}MB")
