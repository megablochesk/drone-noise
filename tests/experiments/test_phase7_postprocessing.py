"""Script-level helpers of the Phase 7 post-processing, on the 2 x 2 grid used for the exposure metrics."""
import numpy as np
import pandas as pd
import pytest

from experiments.revision.run_phase7_postprocessing import (
    average_over_seeds,
    summarise_trip_distances,
    sweep_baseline_default,
    sweep_source_level,
)
from metrics.cell_table import CellTable

CELL_TABLE = CellTable(
    rows=np.array([0, 0, 1, 1]), columns=np.array([0, 1, 0, 1]),
    baseline_levels_db=np.array([40.0, 54.0, 56.0, 54.9]), population=np.array([100.0, 200.0, 300.0, 400.0]),
)
DRONE_LEVELS_DB = np.array([30.0, 50.0, 60.0, 54.9])
RUN = pd.Series({
    "run_key": "abc", "seed": 1, "number_of_drones": 1250, "terminal_phases": False, "stocking": "closest",
    "delivered_orders": 2_000,
})


def test_source_level_sweep_covers_eighty_to_one_hundred_and_five_plus_the_penalty_case():
    """Brief: 80-105 dB in 1 dB steps (26 levels) plus the +5.6 dB annoyance penalty (95.6 dB)."""
    sweep = pd.DataFrame(sweep_source_level(RUN, DRONE_LEVELS_DB, CELL_TABLE))
    assert sweep["noise_at_source_db"].tolist() == [*range(80, 106), 95.6]
    assert sweep["is_annoyance_penalty_case"].tolist() == [False] * 26 + [True]


def test_sweep_at_the_published_source_level_is_the_unshifted_map():
    """At 90 dB nothing shifts: 600 newly exposed and 300 inside the 55 dB contour (2 x 2 grid oracle);
    at 95 dB the 55 dB contour holds cells 2-4, i.e. 900 people."""
    sweep = pd.DataFrame(sweep_source_level(RUN, DRONE_LEVELS_DB, CELL_TABLE)).set_index("noise_at_source_db")
    assert sweep.loc[90, "newly_exposed_population_55db"] == 600.0
    assert sweep.loc[90, "population_inside_drone_contour_55db"] == 300.0
    assert sweep.loc[95, "population_inside_drone_contour_55db"] == 900.0


def test_baseline_default_sweep_has_the_four_defaults_and_keeps_forty_unchanged():
    """Brief: defaults 35 / 40 / 45 / 50 dB; 40 dB is the published baseline (600 newly exposed)."""
    sweep = pd.DataFrame(sweep_baseline_default(RUN, DRONE_LEVELS_DB, CELL_TABLE)).set_index("baseline_default_db")
    assert sweep.index.tolist() == [35.0, 40.0, 45.0, 50.0]
    assert sweep.loc[40.0, "newly_exposed_population_55db"] == 600.0


def test_trip_distance_summary():
    """Trips of 1, 7, 13 and 20 km: mean 10.25 km; two of four exceed 12 km one way; three of four exceed
    12 km as a round trip (twice 7 km is 14 km)."""
    summary = summarise_trip_distances(RUN, np.array([1_000.0, 7_000.0, 13_000.0, 20_000.0]))
    assert summary["mean_trip_distance_m"] == 10_250.0
    assert summary["share_of_trips_beyond_12km_one_way"] == 0.5
    assert summary["share_of_trips_beyond_12km_round_trip"] == 0.75
    assert summary["trip_distance_quantile_50_m"] == 10_000.0


def test_seed_average_reports_mean_and_sample_standard_deviation():
    """Values 1 and 3 over two seeds: mean 2, sample SD sqrt(2)."""
    by_run = pd.DataFrame({
        "seed": [1, 2], "number_of_drones": [1250, 1250], "terminal_phases": [False, False],
        "stocking": ["closest", "closest"], "delivered_orders": [1.0, 3.0],
    })
    averaged = average_over_seeds(by_run, [])
    assert averaged["number_of_seeds"].tolist() == [2]
    assert averaged["delivered_orders_mean"].tolist() == [2.0]
    assert averaged["delivered_orders_sd"].iloc[0] == pytest.approx(2 ** 0.5)
