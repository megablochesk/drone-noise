from __future__ import annotations

from typing import Sequence, Mapping

import pandas as pd
from matplotlib import pyplot as plt

from visualiser.plot_utils import get_color_map

DATASET_TYPE_LINE_ORDER = ["furthest", "closest", "random"]

LEGEND_TITLE = "Warehouse Stock Conditions"

DATASET_TYPE_TO_LEGEND = {
    "furthest": "worst-case stocking",
    "closest": "best-case stocking",
    "random": "random stocking",
}


def plot_linegraph_stats(
    results_df: pd.DataFrame,
    value_column: str,
    xlabel: str,
    ylabel: str,
    title: str | None = None,
    filename: str | None = None,
) -> plt.Figure:
    dataset_types = [
        ds for ds in DATASET_TYPE_LINE_ORDER if ds in results_df["dataset_name"].unique()
    ]
    num_drones = sorted(results_df["num_drones"].unique())
    color_map = get_color_map(dataset_types)

    return _plot_dataset_linegraph(
        results=results_df,
        num_drones=num_drones,
        dataset_order=dataset_types,
        value_column=value_column,
        color_map=color_map,
        xlabel=xlabel,
        ylabel=ylabel,
        title=title,
        filename=filename,
    )


def plot_combined_lines(
    df: pd.DataFrame,
    value_column: str,
    *,
    dataset_col: str = "dataset",
    group_col: str = "num_drones",
    nav_col: str = "navigation_type",
    nav_map: Mapping[str, str] | None = None,
    title: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    filename: str | None = None,
):
    if nav_map is None:
        nav_map = {"STRAIGHT": "Normal", "LIGHT_NOISE": "Routed"}
    if ylabel is None:
        ylabel = value_column

    drone_counts = sorted(df[group_col].unique())
    datasets = sorted(df[dataset_col].unique())
    nav_types = list(nav_map.keys())

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.filename = filename

    _plot_nav_grouped_lines(
        ax,
        df,
        datasets=datasets,
        drone_counts=drone_counts,
        nav_types=nav_types,
        nav_map=nav_map,
        dataset_col=dataset_col,
        group_col=group_col,
        nav_col=nav_col,
        value_col=value_column,
    )

    _finalise_axes(ax, xlabel=xlabel, ylabel=ylabel, title=title or value_column, legend_ncol=2)
    return fig, ax


def _plot_dataset_linegraph(
    *,
    results: pd.DataFrame,
    num_drones: Sequence[int],
    dataset_order: Sequence[str],
    value_column: str,
    color_map: Mapping[str, str],
    xlabel: str,
    ylabel: str,
    title: str | None,
    filename: str | None = None,
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(13, 6))
    fig.filename = filename

    for ds in dataset_order:
        values = []
        for drones in num_drones:
            row = results.query("dataset_name == @ds and num_drones == @drones")
            val = 0 if row.empty else row.iloc[0][value_column]
            values.append(val)

        legend_label = DATASET_TYPE_TO_LEGEND.get(ds, ds)
        ax.plot(
            num_drones,
            values,
            marker="o",
            color=color_map[ds],
            label=legend_label,
            linewidth=2,
            markersize=6,
        )

    _finalise_axes(ax, xlabel=xlabel, ylabel=ylabel, title=title or "", legend_title=LEGEND_TITLE)
    return fig


def _plot_nav_grouped_lines(
    ax,
    df: pd.DataFrame,
    *,
    datasets: Sequence[str],
    drone_counts: Sequence[int],
    nav_types: Sequence[str],
    nav_map: Mapping[str, str],
    dataset_col: str,
    group_col: str,
    nav_col: str,
    value_col: str,
):
    cmap = plt.get_cmap("tab10")
    colors = {ds: cmap(i % 10) for i, ds in enumerate(datasets)}
    linestyles = {nav_types[i]: style for i, style in enumerate(["-", "--", ":", "-."])}

    for dataset_value in datasets:
        for nav in nav_types:
            vals = []
            for drone_count in drone_counts:
                match = df.loc[
                    (df[dataset_col] == dataset_value)
                    & (df[group_col] == drone_count)
                    & (df[nav_col] == nav),
                    value_col,
                ]
                vals.append(match.squeeze() if not match.empty else 0)

            legend_label = f"{nav_map[nav]}-{DATASET_TYPE_TO_LEGEND.get(dataset_value, dataset_value)}"
            ax.plot(
                drone_counts,
                vals,
                marker="o",
                color=colors[dataset_value],
                linestyle=linestyles.get(nav, "-"),
                label=legend_label,
                linewidth=2,
                markersize=5,
            )


def _finalise_axes(ax, *, xlabel, ylabel, title, legend_ncol=1, legend_title=None):
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    ax.legend(ncol=legend_ncol, title=legend_title)
    ax.grid(axis="both", linestyle=":", linewidth=0.7, alpha=0.6)
    ax.figure.tight_layout()