import numpy as np
import pytest

from noise.noise_tracker import calculate_cells_noise
from tests.legacy_reference import load_legacy_module

LEGACY_MATH_MODULE = load_legacy_module("noise/noise_math_utils.py")
LEGACY_TRACKER_MODULE = load_legacy_module(
    "noise/noise_tracker.py", legacy_dependencies={"noise.noise_math_utils": LEGACY_MATH_MODULE}
)
PUBLISHED_SOURCE_LEVEL_DB = 90.0


def random_scene(number_of_cells: int, number_of_drones: int, seed: int) -> tuple[np.ndarray, ...]:
    generator = np.random.default_rng(seed)
    cell_northings = generator.uniform(156_000, 200_000, number_of_cells)
    cell_eastings = generator.uniform(504_000, 561_000, number_of_cells)
    drone_northings = generator.uniform(156_000, 200_000, number_of_drones)
    drone_eastings = generator.uniform(504_000, 561_000, number_of_drones)
    drone_altitudes = generator.choice([0.0, 50.0, 100.0], number_of_drones)
    return cell_northings, cell_eastings, drone_northings, drone_eastings, drone_altitudes


@pytest.mark.parametrize("number_of_drones", [0, 1, 37])
def test_default_source_level_matches_the_published_kernel(number_of_drones):
    """Characterisation: expected levels come from the kernel source at the published baseline commit."""
    scene = random_scene(number_of_cells=50, number_of_drones=number_of_drones, seed=7)
    current_levels = calculate_cells_noise(*scene, PUBLISHED_SOURCE_LEVEL_DB)
    legacy_levels = LEGACY_TRACKER_MODULE.calculate_cells_noise(*scene)
    np.testing.assert_array_equal(current_levels, legacy_levels)


@pytest.mark.parametrize("source_level_increase_db", [1.0, 5.6, 15.0])
def test_raising_the_source_level_raises_every_cell_by_the_same_amount(source_level_increase_db):
    """Invariant: the source level is an additive term in decibels, so the map shifts by exactly X dB."""
    scene = random_scene(number_of_cells=50, number_of_drones=20, seed=11)
    reference_levels = calculate_cells_noise(*scene, PUBLISHED_SOURCE_LEVEL_DB)
    raised_levels = calculate_cells_noise(*scene, PUBLISHED_SOURCE_LEVEL_DB + source_level_increase_db)
    np.testing.assert_allclose(raised_levels - reference_levels, source_level_increase_db, rtol=0, atol=1e-9)
