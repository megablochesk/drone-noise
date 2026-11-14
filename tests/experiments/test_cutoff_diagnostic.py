"""Diagnostic: what the noise sum loses when positions beyond a maximum slant distance are left out."""
import numpy as np
import pytest

from experiments.revision.cutoff_diagnostic import calculate_levels_within_cutoffs, summarise_cutoff_errors
from noise.energy_noise import FlightSamples

SOURCE_DB = 100.0


def test_levels_within_a_cutoff_leave_out_the_positions_beyond_it():
    """Receiver at the origin, ground-level positions at 10 m and 1,000 m, one time step.

    Exact: 100 + 10 log10(1/10^2 + 1/1000^2) = 100 + 10 log10(0.010001); within 500 m only the near one: 80 dB.
    """
    samples = FlightSamples(
        northings=np.array([0.0, 0.0]), eastings=np.array([10.0, 1000.0]), altitudes_m=np.array([0.0, 0.0])
    )

    levels = calculate_levels_within_cutoffs(
        np.array([0.0]), np.array([0.0]), samples, number_of_time_steps=1, noise_at_source_db=SOURCE_DB,
        maximum_slant_distances_m=[np.inf, 500.0, 5.0],
    )

    assert list(levels) == [np.inf, 500.0, 5.0]
    assert levels[np.inf][0] == pytest.approx(100.0 + 10.0 * np.log10(0.010001), abs=1e-12)
    assert levels[500.0][0] == pytest.approx(80.0, abs=1e-12)
    assert levels[5.0][0] == -np.inf


def test_cutoff_errors_are_measured_on_the_combined_level_against_the_exact_sum():
    """Two cells with a 50 dB baseline and 100 and 200 residents; the cut-off silences the second cell.

    Exact combined levels: 10 log10(10^5.6 + 10^5) = 56.973 dB and 10 log10(10^5.4 + 10^5) = 55.455 dB, so both
    cells cross 55 dB (300 residents). With the cut-off the second cell stays at 50 dB (100 residents).
    """
    baseline_levels_db, population = np.array([50.0, 50.0]), np.array([100.0, 200.0])
    levels_by_cutoff = {np.inf: np.array([56.0, 54.0]), 2000.0: np.array([56.0, -np.inf])}
    exact_combined = 10.0 * np.log10(10.0 ** np.array([5.6, 5.4]) + 10.0 ** 5.0)

    table = summarise_cutoff_errors(levels_by_cutoff, baseline_levels_db, population).set_index("maximum_slant_distance_m")

    assert list(table.index) == [np.inf, 2000.0]
    assert table.loc[np.inf, "largest_combined_level_error_db"] == 0.0
    assert table.loc[2000.0, "largest_combined_level_error_db"] == pytest.approx(exact_combined[1] - 50.0, abs=1e-9)
    assert table.loc[np.inf, "mean_noise_increase_db"] == pytest.approx(np.mean(exact_combined - 50.0), abs=1e-9)
    assert table.loc[2000.0, "mean_noise_increase_db"] == pytest.approx((exact_combined[0] - 50.0) / 2.0, abs=1e-9)
    assert table.loc[np.inf, "newly_exposed_population_55db"] == 300.0
    assert table.loc[2000.0, "newly_exposed_population_55db"] == 100.0
