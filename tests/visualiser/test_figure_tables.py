"""Tables behind the figures: pure functions from run tables and arrays, without any drawing."""
import numpy as np
import pandas as pd
import pytest

from visualiser.figure_tables import (
    build_grid_image,
    count_cells_by_noise_increase,
    find_shared_colour_range,
    measure_route_lengths,
    summarise_group_exposure,
    tabulate_metric_by_fleet,
)


def build_runs() -> pd.DataFrame:
    """Two fleets x two stockings, straight routing with terminal phases, plus one noise-aware run."""
    return pd.DataFrame({
        "number_of_drones": [500, 100, 500, 100, 500],
        "stocking": ["closest", "closest", "furthest", "furthest", "closest"],
        "terminal_phases": True,
        "navigation": ["STRAIGHT", "STRAIGHT", "STRAIGHT", "STRAIGHT", "NOISE_A050"],
        "delivered_orders": [50, 10, 30, 6, 45],
    })


def test_metric_is_tabulated_by_fleet_for_one_routing_and_terminal_mode():
    table = tabulate_metric_by_fleet(build_runs(), "delivered_orders", terminal_phases=True, navigation="STRAIGHT")

    assert table.index.tolist() == [100, 500]
    assert table["closest"].tolist() == [10, 50] and table["furthest"].tolist() == [6, 30]


def test_rows_without_a_routing_count_as_straight():
    """A run table without routing values holds straight-line runs."""
    runs = build_runs().astype({"navigation": object})
    runs.loc[runs["navigation"] == "STRAIGHT", "navigation"] = np.nan

    table = tabulate_metric_by_fleet(runs, "delivered_orders", terminal_phases=True, navigation="STRAIGHT")

    assert table["closest"].tolist() == [10, 50]


def test_a_missing_or_repeated_run_is_refused():
    runs = build_runs()

    with pytest.raises(ValueError, match="exactly one run"):
        tabulate_metric_by_fleet(runs.iloc[1:], "delivered_orders", terminal_phases=True, navigation="STRAIGHT")
    with pytest.raises(ValueError, match="exactly one run"):
        tabulate_metric_by_fleet(pd.concat([runs, runs.iloc[:1]]), "delivered_orders", terminal_phases=True, navigation="STRAIGHT")


def test_group_exposure_is_the_newly_exposed_cells_share_of_each_group():
    """Three cells, the first and third newly exposed. Group 1: (10 + 30) of 60 = 66.67 %; group 2: 0 of 5."""
    newly_exposed = np.array([True, False, True])
    group_counts = {1: np.array([10.0, 20.0, 30.0]), 2: np.array([0.0, 5.0, 0.0])}

    summary = summarise_group_exposure(newly_exposed, group_counts, {1: "first", 2: "second"})

    assert summary["name"].tolist() == ["first", "second"]
    assert summary["newly_exposed"].tolist() == [40.0, 0.0]
    assert summary["total"].tolist() == [60.0, 5.0]
    assert summary["share"].tolist() == pytest.approx([40.0 / 60.0, 0.0])


def test_maps_of_one_figure_share_the_range_of_their_finite_values():
    """Percentiles 0 and 100 of the finite values of all maps together."""
    maps = [np.array([[1.0, np.nan], [3.0, 5.0]]), np.array([[-np.inf, 2.0], [9.0, 4.0]])]

    assert find_shared_colour_range(maps, lower_percentile=0.0, upper_percentile=100.0) == (1.0, 9.0)


def test_cell_values_are_placed_by_row_and_column_and_missing_cells_are_blank():
    """Cells (0, 0), (0, 2) and (1, 1) of a 2 x 3 grid; the other three are not part of the study area."""
    image = build_grid_image(np.array([0, 0, 1]), np.array([0, 2, 1]), np.array([5.0, 7.0, 9.0]))

    assert image.shape == (2, 3)
    assert image[0, 0] == 5.0 and image[0, 2] == 7.0 and image[1, 1] == 9.0
    assert np.isnan(image[0, 1]) and np.isnan(image[1, 0]) and np.isnan(image[1, 2])


def test_cells_are_counted_in_half_decibel_bins_of_their_noise_increase():
    """Increases 0.1, 0.2, 0.7, 1.4 dB with bins of 0.5 dB from floor(min) = 0 to ceil(max) = 2:
    two cells in 0-0.5, one in 0.5-1.0, one in 1.0-1.5."""
    labels, counts = count_cells_by_noise_increase(np.array([0.1, 0.2, 0.7, 1.4]), bin_width_db=0.5)

    assert counts == [2, 1, 1]
    assert labels[1:] == ["0.5 - 1.0", "1.0 - 1.5"]


def test_route_lengths_are_compared_with_the_straight_route():
    """Straight: 3-4-5 triangle, 5 km. Detour along the two legs: 7 km, 40 % longer."""
    routes = {
        "STRAIGHT": (np.array([0.0, 3000.0]), np.array([0.0, 4000.0])),
        "NOISE_A100": (np.array([0.0, 3000.0, 3000.0]), np.array([0.0, 0.0, 4000.0])),
    }

    lengths = measure_route_lengths(routes).set_index("navigation")

    assert lengths["route_length_km"].tolist() == [5.0, 7.0]
    assert lengths.loc["NOISE_A100", "increase_over_straight"] == pytest.approx(0.4)


def build_seeded_runs() -> pd.DataFrame:
    """One fleet, two stockings, seeds 1 and 2."""
    return pd.DataFrame({
        "number_of_drones": 100, "stocking": ["closest", "closest", "furthest", "furthest"], "terminal_phases": True,
        "navigation": "STRAIGHT", "seed": [1, 2, 1, 2], "delivered_orders": [10, 14, 6, 8],
    })


def test_a_metric_is_averaged_over_the_seeds_of_each_fleet_and_stocking():
    from visualiser.figure_tables import count_seeds

    runs = build_seeded_runs()
    table = tabulate_metric_by_fleet(runs, "delivered_orders", terminal_phases=True, navigation="STRAIGHT")

    assert table.loc[100, "closest"] == 12.0 and table.loc[100, "furthest"] == 7.0
    assert count_seeds(runs) == 2


def test_fleets_or_stockings_with_different_seeds_are_refused():
    """A mean over seeds 1-2 next to a mean over seed 1 alone would not be comparable."""
    runs = build_seeded_runs().iloc[:3]

    with pytest.raises(ValueError, match="same seeds"):
        tabulate_metric_by_fleet(runs, "delivered_orders", terminal_phases=True, navigation="STRAIGHT")


def test_maps_of_several_seeds_are_averaged_as_sound_energy():
    """50 dB and 60 dB: 10 log10((10^5 + 10^6) / 2) = 57.404 dB, not 55 dB."""
    from visualiser.figure_tables import average_levels_db

    averaged = average_levels_db([np.array([50.0, 40.0]), np.array([60.0, 40.0])])

    assert averaged == pytest.approx([57.4036, 40.0], abs=1e-4)


def test_group_exposure_is_averaged_over_seeds():
    """Seed 1 exposes the first cell, seed 2 the first two: group 1 has (10 + 30) / 2 = 20 newly exposed of 60."""
    from visualiser.figure_tables import average_group_exposure

    group_counts = {1: np.array([10.0, 20.0, 30.0])}
    summaries = [
        summarise_group_exposure(mask, group_counts, {1: "first"})
        for mask in (np.array([True, False, False]), np.array([True, True, False]))
    ]

    averaged = average_group_exposure(summaries)

    assert averaged["name"].tolist() == ["first"]
    assert averaged["newly_exposed"].tolist() == [20.0] and averaged["total"].tolist() == [60.0]
    assert averaged["share"].tolist() == pytest.approx([20.0 / 60.0])
