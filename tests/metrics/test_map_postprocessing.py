"""Post-processing of saved drone-only maps, on hand-built cells."""
import numpy as np
import pytest

from metrics.map_postprocessing import (
    rebase_baseline_default,
    summarise_map_exposure,
    summarise_per_thousand_deliveries,
)

BASELINE_LEVELS_DB = np.array([40.0, 54.0, 56.0, 54.9])
DRONE_LEVELS_DB = np.array([30.0, 50.0, 60.0, 54.9])
POPULATION = np.array([100.0, 200.0, 300.0, 400.0])


def test_exposure_summary_of_the_two_by_two_grid():
    """Same grid as test_exposure_metrics.py: newly exposed 0 / 600 / 300 at 50 / 55 / 60 dB, drone-only
    contour population 700 at 51 dB and 300 at 55 dB, mean increase 2.58 dB."""
    summary = summarise_map_exposure(DRONE_LEVELS_DB, BASELINE_LEVELS_DB, POPULATION)
    assert summary["newly_exposed_population_50db"] == 0.0
    assert summary["newly_exposed_population_55db"] == 600.0
    assert summary["newly_exposed_population_60db"] == 300.0
    assert summary["population_inside_drone_contour_51db"] == 700.0
    assert summary["population_inside_drone_contour_55db"] == 300.0
    assert summary["mean_noise_increase_db"] == pytest.approx(2.58, abs=0.005)


def test_raising_the_source_level_is_a_shift_of_the_drone_only_map():
    """Shifting the map by +5 dB: drone levels 35, 55, 65, 59.9 -> contour at 55 dB holds cells 2, 3, 4 (900)."""
    summary = summarise_map_exposure(DRONE_LEVELS_DB + 5.0, BASELINE_LEVELS_DB, POPULATION)
    assert summary["population_inside_drone_contour_55db"] == 900.0


def test_rebasing_the_default_keeps_the_published_baseline_at_forty():
    """Identity: a 40 dB default is what the file already contains."""
    baseline = np.array([40.0, 40.007, 48.75, 57.5, 70.0])
    np.testing.assert_allclose(rebase_baseline_default(baseline, 40.0), baseline)


def test_rebasing_the_default_moves_only_the_unmapped_share_of_a_cell():
    """Model: a cell value is default + covered_share * (57.5 - default) for the lowest mapped band, so
    covered_share = (value - 40) / 17.5 and the cell moves by (new - 40) * (1 - covered_share).
    To 45 dB: 40 -> 45; 40.007 (share 0.0004) -> 40.007 + 5 * 0.9996 = 45.005; 48.75 (share 0.5) -> 51.25;
    57.5 and 70 (fully mapped) stay. To 35 dB: 40 -> 35; 48.75 -> 46.25."""
    baseline = np.array([40.0, 40.007, 48.75, 57.5, 70.0])
    np.testing.assert_allclose(rebase_baseline_default(baseline, 45.0), [45.0, 45.005, 51.25, 57.5, 70.0], atol=1e-9)
    np.testing.assert_allclose(rebase_baseline_default(baseline, 35.0)[[0, 2]], [35.0, 46.25], atol=1e-9)


def test_per_thousand_delivery_columns():
    """600 newly exposed over 2,000 deliveries is 300 per 1,000; 2.58 dB over 2,000 deliveries is 1.29."""
    per_thousand = summarise_per_thousand_deliveries(
        {"newly_exposed_population_55db": 600.0, "mean_noise_increase_db": 2.58}, delivered_orders=2_000
    )
    assert per_thousand == pytest.approx({
        "newly_exposed_population_55db_per_1000_deliveries": 300.0,
        "mean_noise_increase_db_per_1000_deliveries": 1.29,
    })
