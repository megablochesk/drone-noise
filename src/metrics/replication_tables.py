"""Replication statistics laid out as tables: one row per configuration (and per pair of levels)."""
from dataclasses import asdict
from itertools import combinations

import pandas as pd

from metrics.replication_statistics import (
    calculate_required_replicates,
    summarise_paired_differences,
    summarise_replicates,
)


def describe_group(group_columns: list[str], group_key) -> dict:
    group_values = group_key if isinstance(group_key, tuple) else (group_key,)
    return dict(zip(group_columns, group_values))


def summarise_metric_by_configuration(
        runs: pd.DataFrame, metric: str, group_columns: list[str], relative_half_width: float
) -> pd.DataFrame:
    rows = []
    for group_key, group in runs.groupby(group_columns, sort=False):
        values = group[metric].to_numpy()
        rows.append({
            **describe_group(group_columns, group_key),
            "metric": metric,
            **asdict(summarise_replicates(values)),
            "required_replicates": calculate_required_replicates(values, relative_half_width),
        })
    return pd.DataFrame(rows)


def summarise_paired_differences_between_levels(
        runs: pd.DataFrame, metric: str, level_column: str, pair_column: str, group_columns: list[str]
) -> pd.DataFrame:
    """For every pair of levels (e.g. two stockings), the difference first - second matched on `pair_column`."""
    rows = []
    for group_key, group in runs.groupby(group_columns, sort=False):
        by_pair = group.pivot(index=pair_column, columns=level_column, values=metric).dropna()
        for first_level, second_level in combinations(by_pair.columns, 2):
            summary = summarise_paired_differences(by_pair[first_level].to_numpy(), by_pair[second_level].to_numpy())
            rows.append({
                **describe_group(group_columns, group_key), "metric": metric,
                "first_level": first_level, "second_level": second_level, **asdict(summary),
            })
    return pd.DataFrame(rows)
