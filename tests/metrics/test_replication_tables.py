"""Replication tables on a hand-built run table (values chosen so the statistics are easy to do by hand)."""
import pandas as pd
import pytest

from metrics.replication_tables import summarise_metric_by_configuration, summarise_paired_differences_between_levels

RUNS = pd.DataFrame({
    "number_of_drones": [100] * 6,
    "stocking": ["closest"] * 3 + ["random"] * 3,
    "seed": [1, 2, 3, 3, 1, 2],
    "delivered_orders": [10.0, 12.0, 14.0, 11.0, 9.0, 10.0],
})


def test_metric_summary_per_configuration():
    """closest: 10, 12, 14 -> mean 12, SD 2, CV 1/6, half-width 4.303 * 2 / sqrt(3) = 4.968.
    random: 9, 10, 11 -> mean 10, SD 1, CV 0.1, half-width 2.484."""
    summary = summarise_metric_by_configuration(
        RUNS, "delivered_orders", ["number_of_drones", "stocking"], relative_half_width=0.05
    )
    closest = summary[summary["stocking"] == "closest"].iloc[0]
    random_stocking = summary[summary["stocking"] == "random"].iloc[0]

    assert (closest["metric"], closest["number_of_replicates"]) == ("delivered_orders", 3)
    assert (closest["mean"], closest["standard_deviation"]) == pytest.approx((12.0, 2.0))
    assert closest["coefficient_of_variation"] == pytest.approx(1 / 6)
    assert closest["confidence_half_width"] == pytest.approx(4.968, abs=5e-4)
    assert (random_stocking["mean"], random_stocking["standard_deviation"]) == pytest.approx((10.0, 1.0))
    assert random_stocking["confidence_half_width"] == pytest.approx(2.484, abs=5e-4)


def test_required_replicates_column_uses_the_relative_target():
    """random: target 0.05 * 10 = 0.5 with SD 1. n = 17: 2.1199 / sqrt(17) = 0.514 (too wide);
    n = 18: 2.1098 / sqrt(18) = 0.497. So 18 seeds (t quantiles for 16 and 17 degrees of freedom)."""
    summary = summarise_metric_by_configuration(
        RUNS, "delivered_orders", ["number_of_drones", "stocking"], relative_half_width=0.05
    )
    assert summary.loc[summary["stocking"] == "random", "required_replicates"].iloc[0] == 18


def test_paired_differences_are_matched_by_seed_not_by_row_order():
    """closest - random by seed: 10-9, 12-10, 14-11 = 1, 2, 3 -> mean 2, SD 1, half-width 2.484.
    (The random rows are deliberately out of seed order.)"""
    differences = summarise_paired_differences_between_levels(
        RUNS, "delivered_orders", level_column="stocking", pair_column="seed", group_columns=["number_of_drones"]
    )
    assert len(differences) == 1
    row = differences.iloc[0]
    assert (row["first_level"], row["second_level"]) == ("closest", "random")
    assert (row["mean"], row["standard_deviation"]) == pytest.approx((2.0, 1.0))
    assert row["confidence_half_width"] == pytest.approx(2.484, abs=5e-4)
    assert row["number_of_replicates"] == 3
