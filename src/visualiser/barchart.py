from __future__ import annotations

from typing import Sequence, Mapping

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from visualiser.plot_utils import get_color_map

DATASET_TYPE_BAR_ORDER = ["furthest", "closest", "random"]

DATASET_TYPE_TO_LEGEND = {
    "furthest": "worst",
    "closest": "best",
    "random": "random",
}


def plot_barchart_stats(
    results_df: pd.DataFrame,
    value_column: str,
    xlabel: str,
    ylabel: str,
    title: str | None = None,
    decimal_places: int = 2,
    filename: str | None = None,
):
    dataset_types = [
        ds for ds in DATASET_TYPE_BAR_ORDER if ds in results_df["dataset_name"].unique()
    ]
    num_drones = sorted(results_df["num_drones"].unique())
    color_map = get_color_map(dataset_types)

    return _plot_dataset_barchart(
        results=results_df,
        num_drones=num_drones,
        dataset_order=dataset_types,
        value_column=value_column,
        color_map=color_map,
        xlabel=xlabel,
        ylabel=ylabel,
        title=title,
        decimals=decimal_places,
        filename=filename,
    )


def plot_combined_bars(
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
    bar_width: float = 0.35,
    decimal_places: int = 0,
    annotate: bool = True,
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
    _plot_nav_grouped_bars(
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
        bar_width=bar_width,
        decimals=decimal_places,
        annotate=annotate,
    )

    _finalise_axes(ax, x_ticks=drone_counts, xlabel=xlabel,
                   ylabel=ylabel, title=title or value_column, legend_ncol=2)
    return fig, ax


def _plot_dataset_barchart(
    *,
    results: pd.DataFrame,
    num_drones: Sequence[int],
    dataset_order: Sequence[str],
    value_column: str,
    color_map: Mapping[str, str],
    xlabel: str,
    ylabel: str,
    title: str | None,
    bar_width: float = 0.27,
    decimals: int = 2,
    filename: str | None = None,
) -> plt.Figure:
    x_positions = np.arange(len(num_drones))
    fig, ax = plt.subplots(figsize=(13, 6))
    fig.filename = filename

    legend_added: set[str] = set()

    for idx, drones in enumerate(num_drones):
        values = _values_for_datasets(results, dataset_order, value_column, drones)
        n_sets = len(values)

        for j, (ds, val) in enumerate(values):
            offset = x_positions[idx] - bar_width * (n_sets - 1) / 2 + j * bar_width
            legend_label = DATASET_TYPE_TO_LEGEND.get(ds, ds)
            label = legend_label if legend_label not in legend_added else ""
            legend_added.add(legend_label)

            bars = ax.bar(offset, val, bar_width, color=color_map[ds], label=label)
            _annotate_single_bar(ax, bars[0], val, decimals)

    _finalise_axes(ax, x_ticks=num_drones, xlabel=xlabel,
                   ylabel=ylabel, title=title or "", legend_title="Dataset type")
    return fig


def _plot_nav_grouped_bars(
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
    bar_width: float,
    decimals: int,
    annotate: bool,
):
    x = np.arange(len(drone_counts))
    w = bar_width / len(datasets)
    cmap = plt.get_cmap("tab10")
    colors = {ds: cmap(i % 10) for i, ds in enumerate(datasets)}

    for i, dataset_value in enumerate(datasets):
        for j, nav in enumerate(nav_types):
            vals = [
                df.loc[
                    (df[dataset_col] == dataset_value)
                    & (df[group_col] == drone_count)
                    & (df[nav_col] == nav),
                    value_col,
                ].squeeze() if not df.loc[
                    (df[dataset_col] == dataset_value)
                    & (df[group_col] == drone_count)
                    & (df[nav_col] == nav),
                    value_col,
                ].empty else 0
                for drone_count in drone_counts
            ]

            offset = (-bar_width/2 if j == 0 else bar_width/2) + i*w
            bars = ax.bar(
                x + offset,
                vals,
                w,
                color=colors[dataset_value],
                alpha=0.6 if nav_map[nav] == "Routed" else 1.0,
                hatch="//" if nav_map[nav] == "Normal" else None,
                label=f"{nav_map[nav]}-{DATASET_TYPE_TO_LEGEND.get(dataset_value, dataset_value)}",
            )

            if annotate:
                for b, v in zip(bars, vals):
                    _annotate_single_bar(ax, b, v, decimals, fontsize=8)


def _values_for_datasets(df: pd.DataFrame, datasets: Sequence[str], value_col: str, drones: int):
    values = []
    for ds in datasets:
        row = df.query("dataset_name == @ds and num_drones == @drones")
        val = 0 if row.empty else row.iloc[0][value_col]
        values.append((ds, val))
    return values


def _annotate_single_bar(ax, bar, value, decimals=2, offset=2, fontsize=10):
    ax.annotate(
        f"{value:.{decimals}f}" if isinstance(value, (float, int)) else str(value),
        xy=(bar.get_x() + bar.get_width() / 2, value),
        xytext=(0, offset),
        textcoords="offset points",
        ha="center", va="bottom", fontsize=fontsize,
    )


def _finalise_axes(ax, *, x_ticks, xlabel, ylabel, title, legend_ncol=1, legend_title=None):
    ax.set_xticks(np.arange(len(x_ticks)))
    ax.set_xticklabels(x_ticks)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(ncol=legend_ncol, title=legend_title)
    ax.grid(axis="y", linestyle=":", linewidth=0.7, alpha=0.6)
    ax.figure.tight_layout()
