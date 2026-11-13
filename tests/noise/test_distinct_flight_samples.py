"""Merging repeated drone positions: the energy sum needs each distinct position once, weighted by its count.

Expected values are hand calculations; the equivalence test uses the unmerged sum as its reference.
"""
import numpy as np
import pytest

from noise.energy_noise import (
    DistinctFlightSamples,
    FlightSamples,
    count_distinct_samples,
    sum_inverse_squared_distances,
    sum_inverse_squared_distances_of_distinct_samples,
)

CELL_NORTHINGS = np.array([0.0, 250.0])
CELL_EASTINGS = np.array([0.0, 750.0])
NO_MINIMUM_DISTANCE_M = 0.0
NO_MAXIMUM_DISTANCE_M = np.inf


def samples_from(points: list[tuple[float, float, float]]) -> FlightSamples:
    northings, eastings, altitudes = (np.array(values, dtype=np.float64) for values in zip(*points))
    return FlightSamples(northings=northings, eastings=eastings, altitudes_m=altitudes)


def as_counted_points(distinct_samples: DistinctFlightSamples) -> dict[tuple[float, float, float], int]:
    return dict(zip(
        zip(distinct_samples.northings.tolist(), distinct_samples.eastings.tolist(), distinct_samples.altitudes_m.tolist()),
        distinct_samples.occurrences.tolist(),
    ))


def test_repeated_positions_are_merged_and_counted():
    samples = samples_from([(1.0, 2.0, 100.0), (3.0, 4.0, 50.0), (1.0, 2.0, 100.0), (1.0, 2.0, 100.0)])
    assert as_counted_points(count_distinct_samples(samples)) == {(1.0, 2.0, 100.0): 3, (3.0, 4.0, 50.0): 1}


def test_positions_differing_in_one_coordinate_only_stay_separate():
    """A drone climbing above its customer keeps its ground position; each altitude is its own sample."""
    points = [(1.0, 2.0, 0.0), (1.0, 2.0, 50.0), (1.0, 9.0, 0.0), (7.0, 2.0, 0.0)]
    assert as_counted_points(count_distinct_samples(samples_from(points))) == dict.fromkeys(points, 1)


def test_no_samples_give_no_distinct_samples():
    empty = FlightSamples(northings=np.array([]), eastings=np.array([]), altitudes_m=np.array([]))
    distinct_samples = count_distinct_samples(empty)
    assert len(distinct_samples.northings) == 0
    assert len(distinct_samples.occurrences) == 0


def test_occurrences_add_up_to_the_number_of_samples():
    generator = np.random.default_rng(5)
    samples = FlightSamples(
        northings=generator.integers(0, 20, 1_000).astype(np.float64),
        eastings=generator.integers(0, 20, 1_000).astype(np.float64),
        altitudes_m=generator.choice([0.0, 50.0, 100.0], 1_000),
    )
    distinct_samples = count_distinct_samples(samples)
    assert distinct_samples.occurrences.sum() == 1_000
    assert len(set(as_counted_points(distinct_samples))) == len(distinct_samples.northings) < 1_000


def test_position_with_three_occurrences_contributes_three_times():
    """Directly overhead at 100 m, three occurrences: 3 / 100^2 = 3e-4 m^-2."""
    distinct_samples = DistinctFlightSamples(
        northings=np.array([0.0]), eastings=np.array([0.0]), altitudes_m=np.array([100.0]), occurrences=np.array([3]),
    )
    sums = sum_inverse_squared_distances_of_distinct_samples(
        CELL_NORTHINGS, CELL_EASTINGS, distinct_samples, NO_MINIMUM_DISTANCE_M, NO_MAXIMUM_DISTANCE_M
    )
    assert sums[0] == pytest.approx(3e-4, rel=1e-12)


@pytest.mark.parametrize("minimum_m, maximum_m", [(0.0, np.inf), (150.0, 2_000.0)])
def test_merged_sum_equals_the_sum_over_every_sample(minimum_m, maximum_m):
    generator = np.random.default_rng(6)
    positions = generator.integers(0, 40, (500, 2)).astype(np.float64) * 125.0
    samples = FlightSamples(positions[:, 0], positions[:, 1], generator.choice([0.0, 50.0, 100.0], 500) + 1.0)
    np.testing.assert_allclose(
        sum_inverse_squared_distances_of_distinct_samples(
            CELL_NORTHINGS, CELL_EASTINGS, count_distinct_samples(samples), minimum_m, maximum_m
        ),
        sum_inverse_squared_distances(CELL_NORTHINGS, CELL_EASTINGS, samples, minimum_m, maximum_m),
        rtol=1e-12,
    )
