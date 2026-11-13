from dataclasses import dataclass

import numpy as np
import pandas as pd
from numba import njit, prange


@dataclass(frozen=True)
class FlightSamples:
    """Positions of every emitting drone at every time step, flattened over steps and drones."""
    northings: np.ndarray
    eastings: np.ndarray
    altitudes_m: np.ndarray


@dataclass(frozen=True)
class DistinctFlightSamples:
    """Every distinct drone position once, with the number of samples flown at it."""
    northings: np.ndarray
    eastings: np.ndarray
    altitudes_m: np.ndarray
    occurrences: np.ndarray


def count_distinct_samples(samples: FlightSamples) -> DistinctFlightSamples:
    """Drones retrace their routes and wait in place, so most positions are sampled several times."""
    positions = pd.DataFrame({
        "northing": samples.northings, "easting": samples.eastings, "altitude_m": samples.altitudes_m,
    })
    counted = positions.groupby(list(positions.columns), sort=False, dropna=False).size().reset_index(name="occurrences")
    return DistinctFlightSamples(
        northings=counted["northing"].to_numpy(), eastings=counted["easting"].to_numpy(),
        altitudes_m=counted["altitude_m"].to_numpy(), occurrences=counted["occurrences"].to_numpy(),
    )


# reassoc lets the inner reduction vectorise; the result differs from strict summation order by rounding only.
@njit(parallel=True, fastmath={"reassoc", "contract"})
def _sum_inverse_squared_distances_kernel(
        cell_northings, cell_eastings, sample_northings, sample_eastings, sample_squared_altitudes_m2,
        sample_occurrences, minimum_squared_distance_m2, maximum_squared_distance_m2
):
    sums = np.zeros(len(cell_northings), dtype=np.float64)

    for cell in prange(len(cell_northings)):
        cell_northing = cell_northings[cell]
        cell_easting = cell_eastings[cell]

        cell_sum = 0.0
        for sample in range(len(sample_northings)):
            delta_northing = cell_northing - sample_northings[sample]
            delta_easting = cell_easting - sample_eastings[sample]
            squared_distance_m2 = (
                delta_northing * delta_northing + delta_easting * delta_easting + sample_squared_altitudes_m2[sample]
            )
            if squared_distance_m2 < maximum_squared_distance_m2:
                cell_sum += sample_occurrences[sample] / max(squared_distance_m2, minimum_squared_distance_m2)

        sums[cell] = cell_sum

    return sums


def sum_inverse_squared_distances_of_distinct_samples(
        cell_northings: np.ndarray,
        cell_eastings: np.ndarray,
        distinct_samples: DistinctFlightSamples,
        minimum_slant_distance_m: float,
        maximum_slant_distance_m: float,
) -> np.ndarray:
    """Per cell, the sum of occurrences/d^2 over all positions closer than the maximum; d is floored at the minimum."""
    return _sum_inverse_squared_distances_kernel(
        cell_northings, cell_eastings, distinct_samples.northings, distinct_samples.eastings,
        distinct_samples.altitudes_m ** 2, distinct_samples.occurrences.astype(np.float64),
        minimum_slant_distance_m ** 2, maximum_slant_distance_m ** 2,
    )


def sum_inverse_squared_distances(
        cell_northings: np.ndarray,
        cell_eastings: np.ndarray,
        samples: FlightSamples,
        minimum_slant_distance_m: float,
        maximum_slant_distance_m: float,
) -> np.ndarray:
    """Per cell, the sum of 1/d^2 over all samples closer than the maximum; d is floored at the minimum."""
    return sum_inverse_squared_distances_of_distinct_samples(
        cell_northings, cell_eastings, count_distinct_samples(samples), minimum_slant_distance_m, maximum_slant_distance_m
    )


def calculate_equivalent_levels_db(
        inverse_squared_distance_sums: np.ndarray, noise_at_source_db: float, number_of_time_steps: int
) -> np.ndarray:
    with np.errstate(divide="ignore"):
        return noise_at_source_db + 10.0 * np.log10(inverse_squared_distance_sums / number_of_time_steps)
