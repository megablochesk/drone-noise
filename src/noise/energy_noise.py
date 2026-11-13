from dataclasses import dataclass

import numpy as np
from numba import njit, prange


@dataclass(frozen=True)
class FlightSamples:
    """Positions of every emitting drone at every time step, flattened over steps and drones."""
    northings: np.ndarray
    eastings: np.ndarray
    altitudes_m: np.ndarray


# reassoc lets the inner reduction vectorise; the result differs from strict summation order by rounding only.
@njit(parallel=True, fastmath={"reassoc", "contract"})
def _sum_inverse_squared_distances_kernel(
        cell_northings, cell_eastings, sample_northings, sample_eastings, sample_squared_altitudes_m2,
        minimum_squared_distance_m2, maximum_squared_distance_m2
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
                cell_sum += 1.0 / max(squared_distance_m2, minimum_squared_distance_m2)

        sums[cell] = cell_sum

    return sums


def sum_inverse_squared_distances(
        cell_northings: np.ndarray,
        cell_eastings: np.ndarray,
        samples: FlightSamples,
        minimum_slant_distance_m: float,
        maximum_slant_distance_m: float,
) -> np.ndarray:
    """Per cell, the sum of 1/d^2 over all samples closer than the maximum; d is floored at the minimum."""
    return _sum_inverse_squared_distances_kernel(
        cell_northings, cell_eastings, samples.northings, samples.eastings, samples.altitudes_m ** 2,
        minimum_slant_distance_m ** 2, maximum_slant_distance_m ** 2,
    )


def calculate_equivalent_levels_db(
        inverse_squared_distance_sums: np.ndarray, noise_at_source_db: float, number_of_time_steps: int
) -> np.ndarray:
    with np.errstate(divide="ignore"):
        return noise_at_source_db + 10.0 * np.log10(inverse_squared_distance_sums / number_of_time_steps)
