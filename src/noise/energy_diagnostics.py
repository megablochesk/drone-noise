"""Diagnostics on the energy sums: where a cell's drone energy comes from, and single-event levels."""
import numpy as np

from noise.energy_noise import FlightSamples, sum_inverse_squared_distances

NO_MINIMUM_SLANT_DISTANCE_M = 0.0
NO_MAXIMUM_SLANT_DISTANCE_M = np.inf


def select_samples(samples: FlightSamples, selected: np.ndarray) -> FlightSamples:
    return FlightSamples(
        northings=samples.northings[selected], eastings=samples.eastings[selected],
        altitudes_m=samples.altitudes_m[selected],
    )


def sum_all_energy(cell_northings: np.ndarray, cell_eastings: np.ndarray, samples: FlightSamples) -> np.ndarray:
    return sum_inverse_squared_distances(
        cell_northings, cell_eastings, samples, NO_MINIMUM_SLANT_DISTANCE_M, NO_MAXIMUM_SLANT_DISTANCE_M
    )


def calculate_low_altitude_energy_shares(
        cell_northings: np.ndarray, cell_eastings: np.ndarray, samples: FlightSamples, altitude_limit_m: float
) -> np.ndarray:
    """Per cell, the share of drone energy received from samples flown below the altitude limit."""
    low_samples = select_samples(samples, samples.altitudes_m < altitude_limit_m)
    return sum_all_energy(cell_northings, cell_eastings, low_samples) / sum_all_energy(cell_northings, cell_eastings, samples)


def calculate_nearby_energy_shares(
        cell_northings: np.ndarray, cell_eastings: np.ndarray, samples: FlightSamples, slant_distance_limit_m: float
) -> np.ndarray:
    """Per cell, the share of drone energy received from samples closer than the slant distance limit."""
    nearby_energy = sum_inverse_squared_distances(
        cell_northings, cell_eastings, samples, NO_MINIMUM_SLANT_DISTANCE_M, slant_distance_limit_m
    )
    return nearby_energy / sum_all_energy(cell_northings, cell_eastings, samples)


def calculate_event_exposure_levels_db(
        receiver_northings: np.ndarray, receiver_eastings: np.ndarray, samples: FlightSamples,
        noise_at_source_db: float, time_step_s: float,
) -> np.ndarray:
    """Sound exposure level at each receiver of the event described by the samples (one per time step)."""
    energy_sums = sum_all_energy(receiver_northings, receiver_eastings, samples)
    return noise_at_source_db + 10.0 * np.log10(energy_sums * time_step_s)
