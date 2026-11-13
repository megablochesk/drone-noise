"""Exposure metrics on aligned per-cell arrays (drone-only level, baseline level, population)."""
import numpy as np


def combine_levels_db(first_levels_db: np.ndarray, second_levels_db: np.ndarray) -> np.ndarray:
    return 10.0 * np.log10(10.0 ** (first_levels_db / 10.0) + 10.0 ** (second_levels_db / 10.0))


def calculate_mean_noise_increase_db(drone_levels_db: np.ndarray, baseline_levels_db: np.ndarray) -> float:
    """Unweighted mean over cells of the rise of the combined level above the baseline."""
    return np.mean(combine_levels_db(baseline_levels_db, drone_levels_db) - baseline_levels_db)


def find_newly_exposed_cells(
        drone_levels_db: np.ndarray, baseline_levels_db: np.ndarray, threshold_db: float
) -> np.ndarray:
    """Mask of cells whose baseline is below the threshold and whose combined level is above it.

    Both inequalities are strict, as in the published `_impacted_cells`.
    """
    combined_levels_db = combine_levels_db(baseline_levels_db, drone_levels_db)
    return (combined_levels_db > threshold_db) & (baseline_levels_db < threshold_db)


def calculate_newly_exposed_population(
        drone_levels_db: np.ndarray, baseline_levels_db: np.ndarray, population: np.ndarray, threshold_db: float
) -> float:
    return population[find_newly_exposed_cells(drone_levels_db, baseline_levels_db, threshold_db)].sum()


def calculate_population_inside_contour(
        drone_levels_db: np.ndarray, population: np.ndarray, contour_level_db: float
) -> float:
    """Population of cells whose drone-only level reaches the contour level, whatever the baseline."""
    return population[drone_levels_db >= contour_level_db].sum()
