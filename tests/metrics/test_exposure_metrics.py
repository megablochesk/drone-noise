"""Exposure metrics on a hand-built 2 x 2 grid. Every expected value is worked out in the docstrings."""
import math

import numpy as np
import pytest

from metrics.exposure_metrics import (
    calculate_mean_noise_increase_db,
    calculate_newly_exposed_population,
    calculate_population_inside_contour,
    combine_levels_db,
)

BASELINE_LEVELS_DB = np.array([40.0, 54.0, 56.0, 54.9])
DRONE_LEVELS_DB = np.array([30.0, 50.0, 60.0, 54.9])
POPULATION = np.array([100.0, 200.0, 300.0, 400.0])


def hand_combined_level_db(first_level_db: float, second_level_db: float) -> float:
    return 10.0 * math.log10(10.0 ** (first_level_db / 10.0) + 10.0 ** (second_level_db / 10.0))


def test_combined_levels_on_the_grid():
    """40+30 = 40.41, 54+50 = 55.46, 56+60 = 61.46, 54.9+54.9 = 57.91 dB (energy sums)."""
    combined = combine_levels_db(BASELINE_LEVELS_DB, DRONE_LEVELS_DB)
    np.testing.assert_allclose(combined, [40.41, 55.46, 61.46, 57.91], atol=0.005)


def test_silent_drone_layer_leaves_the_baseline_unchanged():
    """A cell that never hears a drone has drone level -inf, i.e. zero energy."""
    combined = combine_levels_db(BASELINE_LEVELS_DB, np.full(4, -np.inf))
    np.testing.assert_allclose(combined, BASELINE_LEVELS_DB, atol=1e-12)


def test_mean_noise_increase():
    """Increases 0.41, 1.46, 5.46 and 3.01 dB average to 2.58 dB."""
    expected = np.mean([
        hand_combined_level_db(baseline, drone) - baseline
        for baseline, drone in zip(BASELINE_LEVELS_DB, DRONE_LEVELS_DB)
    ])
    assert expected == pytest.approx(2.58, abs=0.005)
    assert calculate_mean_noise_increase_db(DRONE_LEVELS_DB, BASELINE_LEVELS_DB) == pytest.approx(expected, abs=1e-12)


def test_newly_exposed_population_at_fifty_five():
    """Cell 2 (55.46) and cell 4 (57.91) cross 55 dB from below: 200 + 400 = 600.
    Cell 1 stays below; cell 3 was already above 55 dB, so it is not newly exposed."""
    assert calculate_newly_exposed_population(DRONE_LEVELS_DB, BASELINE_LEVELS_DB, POPULATION, 55.0) == 600.0


def test_newly_exposed_population_at_other_thresholds():
    """At 60 dB only cell 3 crosses (56 -> 61.46): 300. At 50 dB no cell crosses from below: cell 1 stays at
    40.41 and the other three baselines are already above 50 dB."""
    assert calculate_newly_exposed_population(DRONE_LEVELS_DB, BASELINE_LEVELS_DB, POPULATION, 60.0) == 300.0
    assert calculate_newly_exposed_population(DRONE_LEVELS_DB, BASELINE_LEVELS_DB, POPULATION, 50.0) == 0.0


def test_population_inside_the_drone_only_contour():
    """Drone level >= 51 dB in cells 3 and 4 (300 + 400 = 700); >= 55 dB only in cell 3 (300)."""
    assert calculate_population_inside_contour(DRONE_LEVELS_DB, POPULATION, 51.0) == 700.0
    assert calculate_population_inside_contour(DRONE_LEVELS_DB, POPULATION, 55.0) == 300.0


def test_contour_includes_cells_exactly_on_the_contour_level():
    """Convention: a contour at L dB contains cells at exactly L dB."""
    assert calculate_population_inside_contour(DRONE_LEVELS_DB, POPULATION, 54.9) == 700.0
