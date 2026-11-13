"""Phase 8 comparison tables on hand-built run tables."""
import numpy as np
import pandas as pd
import pytest

from experiments.revision.phase8_tables import (
    compare_minimum_slant_distances,
    compare_time_steps,
    summarise_energy_shares,
    summarise_round_trip_times,
)


def test_energy_share_summary():
    """Shares 0.1, 0.6, 0.9, 0.0 with populations 100..400 and cells 2-3 newly exposed: mean 0.4, median
    0.35, two cells above one half holding 500 people, mean among newly exposed 0.75, population-weighted
    mean (10 + 120 + 270 + 0) / 1000 = 0.4."""
    summary = summarise_energy_shares(
        shares=np.array([0.1, 0.6, 0.9, 0.0]), population=np.array([100.0, 200.0, 300.0, 400.0]),
        newly_exposed=np.array([False, True, True, False]),
    )
    assert summary["mean_share"] == pytest.approx(0.4)
    assert summary["median_share"] == pytest.approx(0.35)
    assert summary["cells_with_majority_share"] == 2
    assert summary["population_in_cells_with_majority_share"] == 500.0
    assert summary["mean_share_in_newly_exposed_cells"] == pytest.approx(0.75)
    assert summary["population_weighted_mean_share"] == pytest.approx(0.4)


def test_round_trip_times_and_the_cost_of_terminal_phases():
    """Cruise only: 1,000 s / 10 deliveries = 100 s. Terminal: 3,400 s / 10 = 340 s. Difference 240 s, which
    is exactly 4 x 60 s; a second seed with 110 s and 350 s keeps the difference and gives means 105 / 345."""
    runs = pd.DataFrame({
        "number_of_drones": [1250] * 4, "stocking": ["closest"] * 4, "seed": [1, 1, 2, 2],
        "terminal_phases": [False, True, False, True], "landing_delay_s": [60] * 4,
        "airborne_drone_seconds": [1_000, 3_400, 1_100, 3_500], "delivered_orders": [10, 10, 10, 10],
    })
    table = summarise_round_trip_times(runs)
    row = table.iloc[0]
    assert (row["seconds_per_delivery_cruise_only"], row["seconds_per_delivery_terminal"]) == (105.0, 345.0)
    assert row["terminal_extra_seconds_per_delivery"] == 240.0
    assert row["expected_extra_seconds_four_landing_delays"] == 240
    assert row["terminal_extra_in_landing_delays"] == 4.0


def test_minimum_slant_distance_changes_are_relative_to_the_unfloored_run_of_the_same_seed():
    """Seed 1: increase 2.0 -> 1.5 dB at 10 m (change -0.5), exposed 1000 -> 900 (-10 %).
    Seed 2: 2.2 -> 1.9 (-0.3), 2000 -> 1900 (-5 %). Means: -0.4 dB and -7.5 %."""
    runs = pd.DataFrame({
        "seed": [1, 1, 2, 2], "minimum_slant_distance_m": [0.0, 10.0, 0.0, 10.0],
        "mean_noise_increase_db": [2.0, 1.5, 2.2, 1.9],
        "newly_exposed_population_55db": [1_000.0, 900.0, 2_000.0, 1_900.0],
        "delivered_orders": [50, 50, 60, 60],
    })
    table = compare_minimum_slant_distances(runs)
    row = table[table["minimum_slant_distance_m"] == 10.0].iloc[0]
    assert row["mean_noise_increase_db_change"] == pytest.approx(-0.4)
    assert row["newly_exposed_population_55db_relative_change"] == pytest.approx(-0.075)
    assert row["number_of_seeds"] == 2


def test_time_step_comparison_and_recommendation_rule():
    """10 s versus 30 s. Row one: +0.10 dB and 2.5x the run time -> recommend 10 s. Row two: +0.01 dB,
    +1 % deliveries, +1 % exposed -> below both thresholds, keep 30 s. Row three: +0.2 dB but 4x the run
    time -> too slow, keep 30 s."""
    runs = pd.DataFrame({
        "number_of_drones": [1250, 1250, 500, 500, 100, 100],
        "stocking": ["closest"] * 6, "terminal_phases": [False] * 6, "time_step_s": [30, 10] * 3,
        "mean_noise_increase_db": [2.00, 2.10, 1.00, 1.01, 0.5, 0.7],
        "newly_exposed_population_55db": [1_000.0, 1_000.0, 500.0, 505.0, 100.0, 100.0],
        "delivered_orders": [100, 100, 200, 202, 50, 50],
        "wall_time_s": [10.0, 25.0, 10.0, 20.0, 10.0, 40.0],
    })
    table = compare_time_steps(runs).set_index("number_of_drones")
    assert table.loc[1250, "mean_noise_increase_db_change"] == pytest.approx(0.10)
    assert table.loc[1250, "wall_time_ratio"] == 2.5
    assert bool(table.loc[1250, "recommend_ten_second_step"]) is True
    assert table.loc[500, "delivered_orders_relative_change"] == pytest.approx(0.01)
    assert bool(table.loc[500, "recommend_ten_second_step"]) is False
    assert bool(table.loc[100, "recommend_ten_second_step"]) is False
