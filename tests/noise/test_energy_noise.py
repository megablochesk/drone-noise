"""Oracle and characterisation tests for the energy-sum noise stage.

Model: a sample at slant distance d contributes energy 10^(S/10) / d^2 to a cell; the equivalent level is
S + 10*log10(sum(1/d^2) / number_of_time_steps). Expected values are hand calculations unless stated.
"""
import numpy as np
import pytest

from noise.energy_noise import (
    FlightSamples,
    calculate_equivalent_levels_db,
    sum_inverse_squared_distances,
)
from noise.noise_math_utils import calculate_leq
from tests.legacy_reference import load_legacy_module

LEGACY_MATH_MODULE = load_legacy_module("noise/noise_math_utils.py")
LEGACY_TRACKER_MODULE = load_legacy_module(
    "noise/noise_tracker.py", legacy_dependencies={"noise.noise_math_utils": LEGACY_MATH_MODULE}
)
NO_MINIMUM_DISTANCE_M = 0.0
NO_MAXIMUM_DISTANCE_M = np.inf


def samples_from(points: list[tuple[float, float, float]]) -> FlightSamples:
    northings, eastings, altitudes = (np.array(values, dtype=np.float64) for values in zip(*points))
    return FlightSamples(northings=northings, eastings=eastings, altitudes_m=altitudes)


def random_samples(number_of_samples: int, seed: int) -> FlightSamples:
    generator = np.random.default_rng(seed)
    return FlightSamples(
        northings=generator.uniform(0.0, 5_000.0, number_of_samples),
        eastings=generator.uniform(0.0, 5_000.0, number_of_samples),
        altitudes_m=generator.choice([50.0, 100.0], number_of_samples),
    )


CELL_NORTHINGS = np.array([0.0, 250.0, 4_000.0])
CELL_EASTINGS = np.array([0.0, 750.0, 1_000.0])


def inverse_square_sums(samples: FlightSamples, minimum_m=NO_MINIMUM_DISTANCE_M, maximum_m=NO_MAXIMUM_DISTANCE_M):
    return sum_inverse_squared_distances(CELL_NORTHINGS, CELL_EASTINGS, samples, minimum_m, maximum_m)


def test_sample_directly_overhead():
    """1 / 100^2 = 1e-4 m^-2 for the cell under the drone."""
    sums = inverse_square_sums(samples_from([(0.0, 0.0, 100.0)]))
    assert sums[0] == pytest.approx(1e-4, rel=1e-12)


def test_slant_distance_uses_both_offsets_and_altitude():
    """Offsets 3 m and 4 m at 12 m altitude: 1 / (9 + 16 + 144) = 1/169."""
    sums = inverse_square_sums(samples_from([(3.0, 4.0, 12.0)]))
    assert sums[0] == pytest.approx(1.0 / 169.0, rel=1e-12)


def test_minimum_slant_distance_caps_the_contribution():
    """A sample 5 m above the cell with a 10 m minimum counts as 1 / 10^2, not 1 / 5^2."""
    sample = samples_from([(0.0, 0.0, 5.0)])
    assert inverse_square_sums(sample)[0] == pytest.approx(1.0 / 25.0, rel=1e-12)
    assert inverse_square_sums(sample, minimum_m=10.0)[0] == pytest.approx(1.0 / 100.0, rel=1e-12)


def test_maximum_slant_distance_selects_nearby_samples_only():
    """Samples at 30 m and 130 m slant distance, 50 m limit: only 1 / 30^2 remains."""
    samples = samples_from([(0.0, 0.0, 30.0), (0.0, 50.0, 120.0)])
    assert inverse_square_sums(samples, maximum_m=50.0)[0] == pytest.approx(1.0 / 900.0, rel=1e-12)


def sum_inverse_squared_distances_by_broadcasting(samples: FlightSamples, minimum_m: float, maximum_m: float):
    """Independent oracle: the full cell-by-sample distance matrix in numpy, one term per sample."""
    squared_distances_m2 = (
        (CELL_NORTHINGS[:, np.newaxis] - samples.northings) ** 2
        + (CELL_EASTINGS[:, np.newaxis] - samples.eastings) ** 2
        + samples.altitudes_m ** 2
    )
    contributions = 1.0 / np.maximum(squared_distances_m2, minimum_m ** 2)
    return np.where(squared_distances_m2 < maximum_m ** 2, contributions, 0.0).sum(axis=1)


def repeat_and_shuffle(samples: FlightSamples, seed: int) -> FlightSamples:
    """Every position one to four times, in random order, as drones retracing a route produce them."""
    generator = np.random.default_rng(seed)
    order = generator.permutation(np.repeat(np.arange(len(samples.northings)), generator.integers(1, 5, len(samples.northings))))
    return FlightSamples(samples.northings[order], samples.eastings[order], samples.altitudes_m[order])


@pytest.mark.parametrize("minimum_m, maximum_m", [(0.0, np.inf), (150.0, np.inf), (0.0, 2_000.0), (150.0, 2_000.0)])
def test_repeated_positions_contribute_once_per_occurrence(minimum_m, maximum_m):
    """Characterisation against the broadcasting oracle: a position flown k times counts k times."""
    samples = repeat_and_shuffle(random_samples(200, seed=3), seed=4)
    np.testing.assert_allclose(
        inverse_square_sums(samples, minimum_m, maximum_m),
        sum_inverse_squared_distances_by_broadcasting(samples, minimum_m, maximum_m),
        rtol=1e-12,
    )


def test_energy_of_two_sample_sets_flown_together_is_the_sum_of_the_separate_maps():
    """Invariant (energy additivity): sum over A union B equals sum over A plus sum over B."""
    first_set, second_set = random_samples(300, seed=1), random_samples(500, seed=2)
    together = FlightSamples(
        northings=np.concatenate([first_set.northings, second_set.northings]),
        eastings=np.concatenate([first_set.eastings, second_set.eastings]),
        altitudes_m=np.concatenate([first_set.altitudes_m, second_set.altitudes_m]),
    )
    np.testing.assert_allclose(
        inverse_square_sums(together), inverse_square_sums(first_set) + inverse_square_sums(second_set), rtol=1e-12
    )


def test_equivalent_level_of_one_overhead_sample():
    """90 dB at 100 m is 50 dB; averaged over 10 time steps it is 50 - 10*log10(10) = 40 dB."""
    sums = np.array([1e-4])
    assert calculate_equivalent_levels_db(sums, 90.0, number_of_time_steps=1)[0] == pytest.approx(50.0, abs=1e-9)
    assert calculate_equivalent_levels_db(sums, 90.0, number_of_time_steps=10)[0] == pytest.approx(40.0, abs=1e-9)


def test_cell_that_never_hears_a_drone_has_no_level():
    """Zero energy has no finite decibel value; it is reported as minus infinity."""
    levels = calculate_equivalent_levels_db(np.array([0.0]), 90.0, number_of_time_steps=5)
    assert levels[0] == -np.inf


@pytest.mark.parametrize("source_level_increase_db", [1.0, 5.6, 15.0])
def test_raising_the_source_level_raises_the_map_by_exactly_that_amount(source_level_increase_db):
    """Invariant: the source level is an additive term in the equivalent level."""
    sums = inverse_square_sums(random_samples(400, seed=3))
    reference = calculate_equivalent_levels_db(sums, 90.0, number_of_time_steps=120)
    raised = calculate_equivalent_levels_db(sums, 90.0 + source_level_increase_db, number_of_time_steps=120)
    np.testing.assert_allclose(raised - reference, source_level_increase_db, rtol=0, atol=1e-12)


def test_equivalent_level_matches_the_published_per_step_calculation():
    """Characterisation: the published path mixes levels per step and then takes Leq over the steps."""
    number_of_time_steps, drones_per_step = 40, 15
    steps = [random_samples(drones_per_step, seed=100 + step) for step in range(number_of_time_steps)]

    per_step_levels = np.array([
        LEGACY_TRACKER_MODULE.calculate_cells_noise(
            CELL_NORTHINGS, CELL_EASTINGS, step.northings, step.eastings, step.altitudes_m
        )
        for step in steps
    ])
    published_levels = np.array([calculate_leq(per_step_levels[:, cell]) for cell in range(len(CELL_NORTHINGS))])

    all_samples = FlightSamples(
        northings=np.concatenate([step.northings for step in steps]),
        eastings=np.concatenate([step.eastings for step in steps]),
        altitudes_m=np.concatenate([step.altitudes_m for step in steps]),
    )
    energy_levels = calculate_equivalent_levels_db(inverse_square_sums(all_samples), 90.0, number_of_time_steps)
    np.testing.assert_allclose(energy_levels, published_levels, rtol=0, atol=1e-9)
