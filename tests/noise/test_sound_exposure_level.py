"""Oracle tests for the sound exposure level (SEL). Expected values are closed-form results, stated per test."""
import math

import numpy as np
import pytest

from noise.noise_math_utils import calculate_sound_exposure_level

SOURCE_LEVEL_DB = 90.0
SPEED_MPS = 27.0
ALTITUDE_M = 100.0
PASS_HALF_DURATION_S = 8_000.0
CLOSED_FORM_PASS_SEL_DB = SOURCE_LEVEL_DB + 10.0 * math.log10(math.pi / (SPEED_MPS * ALTITUDE_M))


def sample_overhead_pass_levels(time_step_s: float) -> np.ndarray:
    """Levels under a straight, level pass with one sample exactly overhead: L = S - 10*log10(h^2 + (v*t)^2)."""
    sample_times_s = np.arange(-PASS_HALF_DURATION_S, PASS_HALF_DURATION_S + time_step_s, time_step_s)
    squared_distances_m2 = ALTITUDE_M ** 2 + (SPEED_MPS * sample_times_s) ** 2
    return SOURCE_LEVEL_DB - 10.0 * np.log10(squared_distances_m2)


def test_constant_level_for_ten_seconds():
    """SEL = L + 10*log10(T / 1 s): 60 dB held for 10 s gives 70 dB."""
    assert calculate_sound_exposure_level(np.full(10, 60.0), time_step_s=1.0) == pytest.approx(70.0, abs=1e-9)


def test_time_step_scales_the_exposure():
    """One 60 dB sample representing 4 s: 60 + 10*log10(4) = 66.02 dB."""
    assert calculate_sound_exposure_level(np.array([60.0]), time_step_s=4.0) == pytest.approx(66.02, abs=0.005)


def test_closed_form_pass_value_is_the_quoted_one():
    """Integral of S / (h^2 + v^2 t^2) dt over all t is S*pi/(v*h): 90 + 10*log10(pi / 2700) = 60.66 dBA."""
    assert CLOSED_FORM_PASS_SEL_DB == pytest.approx(60.66, abs=0.005)


def test_sampled_straight_pass_converges_to_the_closed_form():
    """The sampled SEL approaches the closed form monotonically as the time step shrinks."""
    time_steps_s = [8.0, 4.0, 2.0, 1.0, 0.5]
    absolute_errors_db = [
        abs(calculate_sound_exposure_level(sample_overhead_pass_levels(time_step_s), time_step_s) - CLOSED_FORM_PASS_SEL_DB)
        for time_step_s in time_steps_s
    ]
    assert absolute_errors_db == sorted(absolute_errors_db, reverse=True)
    assert absolute_errors_db[0] > 0.1
    assert absolute_errors_db[-1] < 0.01
