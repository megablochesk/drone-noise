"""Tables behind the paper's figures on the fine-grid design; the drawing itself is not tested."""
import numpy as np
import pandas as pd
import pytest

from experiments.revision.paper_figures import (
    describe_navigation,
    find_shared_colour_range,
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


def test_navigation_names_read_as_in_the_paper():
    assert describe_navigation("STRAIGHT") == "Straight"
    assert describe_navigation("NOISE_A025") == "Mixed (α=0.25)"
    assert describe_navigation("NOISE_A100") == "Mixed (α=1.00)"


def test_metric_is_tabulated_by_fleet_for_one_routing_and_terminal_mode():
    table = tabulate_metric_by_fleet(build_runs(), "delivered_orders", terminal_phases=True, navigation="STRAIGHT")

    assert table.index.tolist() == [100, 500]
    assert table["closest"].tolist() == [10, 50] and table["furthest"].tolist() == [6, 30]


def test_rows_stored_before_the_navigation_field_count_as_straight():
    """The pilot runs were stored before runs recorded their routing; they were all straight-line."""
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
