"""Describing a baseline map and comparing exposure under alternative baselines, on hand-built cells."""
import numpy as np
import pytest

from experiments.revision.summarise_round4_baseline import summarise_baseline_levels, summarise_exposure_under_baselines

FLOOR_DB = 40.0
LEVELS_DB = np.array([40.0, 40.0, 50.0, 56.0, 64.0])
POPULATION = np.array([100.0, 0.0, 300.0, 400.0, 200.0])


def test_baseline_summary_of_five_hand_built_cells():
    """Mean (40 + 40 + 50 + 56 + 64) / 5 = 50; two of five cells at the floor; two of five at 55 dB or more,
    holding 600 of 1,000 people; population-weighted mean (4,000 + 15,000 + 22,400 + 12,800) / 1,000 = 54.2."""
    summary = summarise_baseline_levels(LEVELS_DB, POPULATION, FLOOR_DB)
    assert summary["mean_level_db"] == pytest.approx(50.0)
    assert summary["share_of_cells_at_floor"] == pytest.approx(0.4)
    assert summary["share_of_cells_at_or_above_55db"] == pytest.approx(0.4)
    assert summary["population_at_or_above_55db"] == pytest.approx(600.0)
    assert summary["population_weighted_mean_level_db"] == pytest.approx(54.2)
    assert (summary["minimum_level_db"], summary["maximum_level_db"]) == (40.0, 64.0)


def test_exposure_is_reported_for_every_named_baseline():
    """One 55 dB drone cell holding 300 people. Against a 40 dB baseline the cell rises by
    10 * log10(10^5.5 + 10^4) - 40 = 15.135 dB and its 300 people are newly exposed (combined level above 55 dB);
    against a 56 dB baseline it rises by 2.539 dB and nobody is newly exposed, because they already were."""
    drone_levels_db = np.array([55.0, -np.inf])
    population = np.array([300.0, 500.0])
    baselines = {"quiet": np.array([40.0, 40.0]), "loud": np.array([56.0, 40.0])}

    table = summarise_exposure_under_baselines(drone_levels_db, baselines, population).set_index("baseline")

    assert table.loc["quiet", "mean_noise_increase_db"] == pytest.approx(15.135 / 2, abs=1e-3)
    assert table.loc["quiet", "newly_exposed_population_55db"] == pytest.approx(300.0)
    assert table.loc["loud", "mean_noise_increase_db"] == pytest.approx(2.539 / 2, abs=1e-3)
    assert table.loc["loud", "newly_exposed_population_55db"] == pytest.approx(0.0)
    assert list(table.index) == ["quiet", "loud"]
