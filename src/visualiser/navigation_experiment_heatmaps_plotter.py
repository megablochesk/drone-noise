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


def plot_heatmaps_per_drone_number_and_navigation_type(
    df: pd.DataFrame,
    *,
    target_number_of_drones: int = 1250,
    heatmap_metric: str = "average_noise",
    file_prefix: str | None = None,
):
    sub_dataframe = df[df["num_drones"] == target_number_of_drones]
    plot_noise_heatmaps_per_navigation_type(
        sub_dataframe,
        num_drones=target_number_of_drones,
        metric=heatmap_metric,
        file_prefix=file_prefix or f"noise_maps_{heatmap_metric}",
    )


def plot_noise_heatmaps_per_navigation_type(
    results_df: pd.DataFrame,
    *,
    num_drones: int | None = None,
    metric: str = "average_noise",
    file_prefix: str = "noise_maps",
):
    x = results_df.copy()

    if num_drones is not None:
        x = x[x["num_drones"] == num_drones]

    if x.empty:
        return

    vmin, vmax = _global_metric_range(df=x, metric=metric)

    navigation_types = sorted(x["navigation_type"].dropna().unique().tolist())

    for navigation_type in navigation_types:
        sub = x[x["navigation_type"] == navigation_type]
        if sub.empty:
            continue

        dfs = []
        metrics = []
        titles = []

        for ds in _DATASET_ORDER:
            ds_sub = sub[sub["dataset_name"] == ds]
            heat_df = _aggregate_noise_impacts_mean(ds_sub, metric=metric)

            dfs.append(heat_df)
            metrics.append("average_noise")
            titles.append(_DATASET_TITLES.get(ds, ds))

        suffix = f"__d{int(num_drones)}" if num_drones is not None else ""
        file_name = f"{file_prefix}__{navigation_type}{suffix}"

        plot_noise_level_comparison(
            dfs,
            metrics=metrics,
            titles=titles,
            file_name=file_name,
            vmin=vmin,
            vmax=vmax,
            suptitle=None,
        )


def _global_metric_range(df: pd.DataFrame, metric: str, q_low: float = 0.01, q_high: float = 0.99):
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

    lo_q = float(np.quantile(all_v, q_low))
    hi_q = float(np.quantile(all_v, q_high))

    lo = int(np.floor(lo_q))
    hi = int(np.ceil(hi_q))

    return lo, hi


def _aggregate_noise_impacts_mean(group_df: pd.DataFrame, metric: str) -> pd.DataFrame:
    impacts = _collect_noise_frames(group_df)
    if not impacts:
        raise ValueError("Noise impact frame not found")

    all_cells = pd.concat(impacts, ignore_index=True)

    if metric not in all_cells.columns:
        raise KeyError(f"Metric '{metric}' not found in noise_impact_df columns: {list(all_cells.columns)}")

    g = all_cells.groupby(["row", "col"], as_index=False)[metric].mean()
    return g.rename(columns={metric: "average_noise"})


def _collect_noise_frames(group_df: pd.DataFrame) -> list[pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    for _, r in group_df.iterrows():
        x = r.get("noise_impact_df")
        if isinstance(x, pd.DataFrame) and not x.empty:
            frames.append(x)
    return frames
