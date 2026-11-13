"""Metrics derived after the fact from a saved drone-only level map."""
import numpy as np

from metrics.exposure_metrics import (
    calculate_mean_noise_increase_db,
    calculate_newly_exposed_population,
    calculate_population_inside_contour,
)

NEWLY_EXPOSED_THRESHOLDS_DB = (50, 55, 60)
DRONE_CONTOUR_LEVELS_DB = (51, 55)
HEADLINE_THRESHOLD_DB = 55.0
PUBLISHED_BASELINE_DEFAULT_DB = 40.0
LOWEST_MAPPED_BAND_MIDPOINT_DB = 57.5
DELIVERIES_PER_REPORTING_UNIT = 1_000


def summarise_map_exposure(drone_levels_db: np.ndarray, baseline_levels_db: np.ndarray, population: np.ndarray) -> dict:
    summary = {"mean_noise_increase_db": calculate_mean_noise_increase_db(drone_levels_db, baseline_levels_db)}
    for threshold_db in NEWLY_EXPOSED_THRESHOLDS_DB:
        summary[f"newly_exposed_population_{threshold_db}db"] = calculate_newly_exposed_population(
            drone_levels_db, baseline_levels_db, population, threshold_db
        )
    for contour_level_db in DRONE_CONTOUR_LEVELS_DB:
        summary[f"population_inside_drone_contour_{contour_level_db}db"] = calculate_population_inside_contour(
            drone_levels_db, population, contour_level_db
        )
    return summary


def rebase_baseline_default(baseline_levels_db: np.ndarray, new_default_db: float) -> np.ndarray:
    """Baseline as it would be had unmapped ground been filled with `new_default_db` instead of 40 dB.

    The published baseline is an arithmetic mean of 10 m pixels that are either mapped (band mid-points from
    57.5 dB upwards) or filled with 40 dB. The mapped share of a cell is not stored, so it is estimated as if
    all mapped pixels were in the lowest band; cells at or above 57.5 dB count as fully mapped.
    """
    mapped_share = np.clip(
        (baseline_levels_db - PUBLISHED_BASELINE_DEFAULT_DB)
        / (LOWEST_MAPPED_BAND_MIDPOINT_DB - PUBLISHED_BASELINE_DEFAULT_DB),
        0.0, 1.0,
    )
    return baseline_levels_db + (new_default_db - PUBLISHED_BASELINE_DEFAULT_DB) * (1.0 - mapped_share)


def summarise_per_thousand_deliveries(metrics: dict, delivered_orders: int) -> dict:
    return {
        f"{metric_name}_per_1000_deliveries": value * DELIVERIES_PER_REPORTING_UNIT / delivered_orders
        for metric_name, value in metrics.items()
    }


def summarise_exposure_by_distance_band(
        drone_levels_db: np.ndarray, baseline_levels_db: np.ndarray, population: np.ndarray,
        distances_to_centre_m: np.ndarray, distance_limit_m: float,
) -> dict:
    """The two headline metrics computed separately for cells within and beyond a distance from the centre."""
    summary = {}
    for band_name, in_band in (("within", distances_to_centre_m <= distance_limit_m),
                               ("beyond", distances_to_centre_m > distance_limit_m)):
        summary[f"mean_noise_increase_db_{band_name}"] = calculate_mean_noise_increase_db(
            drone_levels_db[in_band], baseline_levels_db[in_band]
        )
        summary[f"newly_exposed_population_55db_{band_name}"] = calculate_newly_exposed_population(
            drone_levels_db[in_band], baseline_levels_db[in_band], population[in_band], HEADLINE_THRESHOLD_DB
        )
    return summary
