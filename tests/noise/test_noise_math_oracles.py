"""Oracle tests for the decibel arithmetic. Every expected value is a hand calculation, stated per test."""
import math

import numpy as np
import pytest

from noise.noise_math_utils import (
    add_two_decibel_levels,
    calculate_distance,
    calculate_leq,
    calculate_mixed_noise_level,
    calculate_noise_at_distance,
)

DECIBEL_TOLERANCE = 0.005


def test_single_source_at_one_hundred_metres():
    """Inverse-square spreading: 90 - 20*log10(100) = 90 - 40 = 50.0 dB."""
    squared_distance_m2 = calculate_distance(0.0, 0.0, 100.0)
    assert calculate_noise_at_distance(squared_distance_m2) == pytest.approx(50.0, abs=1e-9)


def test_slant_distance_combines_horizontal_offsets_and_altitude():
    """3-4-12 box diagonal: 3^2 + 4^2 + 12^2 = 169 m^2 (the function returns the squared distance)."""
    assert calculate_distance(3.0, 4.0, 12.0) == pytest.approx(169.0, abs=1e-12)


def test_two_equal_sources_add_three_decibels():
    """10*log10(2) = 3.0103 dB, quoted as 3.01 dB."""
    combined = calculate_mixed_noise_level(np.array([60.0, 60.0]))
    assert combined - 60.0 == pytest.approx(3.01, abs=DECIBEL_TOLERANCE)


def test_fifty_five_plus_fifty_five():
    """55 dB + 55 dB = 55 + 10*log10(2) = 58.01 dB."""
    assert add_two_decibel_levels(55.0, 55.0) == pytest.approx(58.01, abs=DECIBEL_TOLERANCE)


@pytest.mark.parametrize("first_level_db, second_level_db", [(40.0, 40.0), (40.0, 55.0), (72.5, 31.0), (0.0, 90.0)])
def test_combined_level_is_at_least_each_component(first_level_db, second_level_db):
    """Invariant: energies are non-negative, so a sum cannot be below either term."""
    combined = add_two_decibel_levels(first_level_db, second_level_db)
    assert combined >= max(first_level_db, second_level_db)
    mixed = calculate_mixed_noise_level(np.array([first_level_db, second_level_db]))
    assert mixed == pytest.approx(combined, abs=1e-9)


@pytest.mark.parametrize("constant_level_db", [35.0, 50.0, 61.7])
def test_leq_of_a_constant_level_is_that_level(constant_level_db):
    """Invariant: the energy mean of identical values is that value."""
    assert calculate_leq(np.full(240, constant_level_db)) == pytest.approx(constant_level_db, abs=1e-9)


def test_leq_is_an_energy_mean_not_an_arithmetic_mean():
    """Half the time at 60 dB and half at 0 energy-equivalent 50 dB: 10*log10((1e6 + 1e5) / 2) = 57.40 dB."""
    expected_leq_db = 10.0 * math.log10((1e6 + 1e5) / 2.0)
    assert calculate_leq(np.array([60.0, 50.0])) == pytest.approx(expected_leq_db, abs=1e-9)
    assert expected_leq_db == pytest.approx(57.40, abs=DECIBEL_TOLERANCE)
