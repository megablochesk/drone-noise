from __future__ import annotations

import numpy as np
import pandas as pd

from visualiser.plot_noise_level_comparison import plot_noise_level_comparison

_DATASET_ORDER = ["closest", "random", "furthest"]
_DATASET_TITLES = {
    "closest": "Best Stocking",
    "random": "Random Stocking",
    "furthest": "Worst Stocking",
}


def plot_heatmaps_per_drone_number_and_navigation_type(df, target_number_of_drones=1250, heatmap_metric="noise_difference"):
    plot_noise_heatmaps_per_navigation_type(
        df[df["num_drones"] == target_number_of_drones],
        num_drones=target_number_of_drones,
        metric=heatmap_metric,
        aggregation_method="mean",
        file_prefix=f"noise_maps_{heatmap_metric}"
    )


def plot_noise_heatmaps_per_navigation_type(
    results_df: pd.DataFrame,
    *,
    num_drones: int | None = None,
    metric: str = "noise_level",
    aggregation_method: str = "mean",
    file_prefix: str = "noise_maps",
):
    results_df_copy = results_df.copy()

    vmin, vmax = _global_metric_range(df=results_df_copy, metric=metric)

    if num_drones is not None:
        results_df_copy = results_df_copy[results_df_copy["num_drones"] == num_drones]

    navigation_types = sorted(results_df_copy["navigation_type"].dropna().unique().tolist())

    for navigation_type in navigation_types:
        sub = results_df_copy[results_df_copy["navigation_type"] == navigation_type]
        if sub.empty:
            continue

        dfs = []
        metrics = []
        titles = []

        for ds in _DATASET_ORDER:
            ds_sub = sub[sub["dataset_name"] == ds]
            heat_df = _aggregate_noise_impacts(ds_sub, metric=metric, aggregation_method=aggregation_method)

            dfs.append(heat_df)
            metrics.append("average_noise")
            titles.append(_DATASET_TITLES.get(ds, ds))

        suffix = f"__d{num_drones}" if num_drones is not None else ""
        file_name = f"{file_prefix}__{navigation_type}{suffix}__{metric}_{aggregation_method}"

        suptitle = f"{navigation_type} | drones={num_drones} | {metric} ({aggregation_method})"
        plot_noise_level_comparison(
            dfs,
            metrics=metrics,
            titles=titles,
            file_name=file_name,
            vmin=vmin,
            vmax=vmax,
            suptitle=suptitle,
        )


def _global_metric_range(df, metric: str, q_low: float = 0.01, q_high: float = 0.99):
    vals = []
    for x in df["noise_impact_df"]:
        if x is None or getattr(x, "empty", True):
            continue
        if metric not in x.columns:
            continue
        col = x[metric].to_numpy()
        col = col[np.isfinite(col)]
        if col.size:
            vals.append(col)

    if not vals:
        return None, None

    all_v = np.concatenate(vals, axis=0)
    lo = float(np.quantile(all_v, q_low))
    hi = float(np.quantile(all_v, q_high))
    return lo, hi


def _aggregate_noise_impacts(group_df: pd.DataFrame, *, metric: str, aggregation_method: str) -> pd.DataFrame:
    impacts = _collect_noise_frames(group_df)
    if not impacts:
        raise ValueError("Noise impact frame not found")

    all_cells = pd.concat(impacts, ignore_index=True)

    if metric not in all_cells.columns:
        raise KeyError(f"Metric '{metric}' not found in noise_impact_df columns: {list(all_cells.columns)}")

    if aggregation_method == "median":
        g = all_cells.groupby(["row", "col"], as_index=False)[metric].median()
    else:
        g = all_cells.groupby(["row", "col"], as_index=False)[metric].mean()

    g = g.rename(columns={metric: "average_noise"})
    return g


def _collect_noise_frames(group_df: pd.DataFrame) -> list[pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    for _, r in group_df.iterrows():
        df = r.get("noise_impact_df")
        if isinstance(df, pd.DataFrame) and not df.empty:
            frames.append(df)
    return frames
