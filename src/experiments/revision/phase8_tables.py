"""Comparison tables of the Phase 8 diagnostics (pure functions of run tables)."""
import numpy as np
import pandas as pd

MAJORITY_SHARE = 0.5
LANDING_DELAYS_EXPECTED_PER_ROUND_TRIP = 4
HEADLINE_NOISE_METRIC = "mean_noise_increase_db"
RELATIVE_METRICS = ("newly_exposed_population_55db", "delivered_orders")
MAXIMUM_WALL_TIME_RATIO = 3.0
MINIMUM_NOISE_CHANGE_DB = 0.05
MINIMUM_RELATIVE_CHANGE = 0.02
PUBLISHED_TIME_STEP_S = 30
FINE_TIME_STEP_S = 10


def summarise_energy_shares(shares: np.ndarray, population: np.ndarray, newly_exposed: np.ndarray) -> dict:
    majority_cells = shares > MAJORITY_SHARE
    return {
        "mean_share": shares.mean(),
        "median_share": np.median(shares),
        "share_quantile_95": np.quantile(shares, 0.95),
        "maximum_share": shares.max(),
        "cells_with_majority_share": np.count_nonzero(majority_cells),
        "population_in_cells_with_majority_share": population[majority_cells].sum(),
        "mean_share_in_newly_exposed_cells": shares[newly_exposed].mean() if newly_exposed.any() else np.nan,
        "population_weighted_mean_share": np.average(shares, weights=population),
    }


def summarise_round_trip_times(runs: pd.DataFrame) -> pd.DataFrame:
    """Airborne seconds per delivery with and without terminal phases, mean over seeds."""
    seconds_per_delivery = runs.assign(seconds=runs["airborne_drone_seconds"] / runs["delivered_orders"])
    table = seconds_per_delivery.pivot_table(
        index=["number_of_drones", "stocking", "landing_delay_s"], columns="terminal_phases", values="seconds"
    ).reset_index()
    table = table.rename(columns={False: "seconds_per_delivery_cruise_only", True: "seconds_per_delivery_terminal"})
    table["terminal_extra_seconds_per_delivery"] = (
        table["seconds_per_delivery_terminal"] - table["seconds_per_delivery_cruise_only"]
    )
    table["expected_extra_seconds_four_landing_delays"] = (
        LANDING_DELAYS_EXPECTED_PER_ROUND_TRIP * table["landing_delay_s"]
    )
    table["terminal_extra_in_landing_delays"] = table["terminal_extra_seconds_per_delivery"] / table["landing_delay_s"]
    table.columns.name = None
    return table


def add_changes_from_reference(table: pd.DataFrame, reference: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Adds absolute change of the noise metric and relative change of the count metrics versus `reference`."""
    merged = table.merge(reference, on=keys, suffixes=("", "_reference"))
    merged[f"{HEADLINE_NOISE_METRIC}_change"] = merged[HEADLINE_NOISE_METRIC] - merged[f"{HEADLINE_NOISE_METRIC}_reference"]
    for metric in RELATIVE_METRICS:
        merged[f"{metric}_relative_change"] = merged[metric] / merged[f"{metric}_reference"] - 1.0
    return merged


def compare_minimum_slant_distances(runs: pd.DataFrame) -> pd.DataFrame:
    """Mean over seeds of the change caused by each slant-distance floor, relative to no floor."""
    unfloored = runs[runs["minimum_slant_distance_m"] == 0.0]
    floored = runs[runs["minimum_slant_distance_m"] > 0.0]
    changes = add_changes_from_reference(floored, unfloored.drop(columns="minimum_slant_distance_m"), ["seed"])
    change_columns = [column for column in changes.columns if column.endswith("_change")]
    grouped = changes.groupby("minimum_slant_distance_m")
    return pd.concat([grouped.size().rename("number_of_seeds"), grouped[change_columns].mean()], axis=1).reset_index()


def compare_time_steps(runs: pd.DataFrame) -> pd.DataFrame:
    """10 s against 30 s per configuration, with the brief's rule for recommending the finer step."""
    keys = ["number_of_drones", "stocking", "terminal_phases"]
    coarse = runs[runs["time_step_s"] == PUBLISHED_TIME_STEP_S].drop(columns="time_step_s")
    fine = runs[runs["time_step_s"] == FINE_TIME_STEP_S]
    table = add_changes_from_reference(fine, coarse, keys)
    table["wall_time_ratio"] = table["wall_time_s"] / table["wall_time_s_reference"]
    metrics_move = (table[f"{HEADLINE_NOISE_METRIC}_change"].abs() > MINIMUM_NOISE_CHANGE_DB) | np.any(
        [table[f"{metric}_relative_change"].abs() > MINIMUM_RELATIVE_CHANGE for metric in RELATIVE_METRICS], axis=0
    )
    table["recommend_ten_second_step"] = (table["wall_time_ratio"] < MAXIMUM_WALL_TIME_RATIO) & metrics_move
    return table
